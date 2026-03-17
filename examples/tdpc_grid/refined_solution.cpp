#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <iterator>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace learned_dfa {
namespace internal {
using std::begin;
using std::end;

template <class It> using iter_ref_t = decltype(*std::declval<It &>());

template <class Range>
using range_begin_t = decltype(begin(std::declval<const Range &>()));

template <class Range>
using range_end_t = decltype(end(std::declval<const Range &>()));

template <class, class = void> struct is_input_iterator : std::false_type {};

template <class It>
struct is_input_iterator<
    It, std::void_t<typename std::iterator_traits<It>::iterator_category,
                    decltype(*std::declval<It &>()),
                    decltype(++std::declval<It &>()),
                    decltype(std::declval<It &>() == std::declval<It &>()),
                    decltype(std::declval<It &>() != std::declval<It &>())>>
    : std::bool_constant<std::is_base_of_v<
          std::input_iterator_tag,
          typename std::iterator_traits<It>::iterator_category>> {};

template <class It>
inline constexpr bool is_input_iterator_v = is_input_iterator<It>::value;

template <class It, class ToIndex, class = void>
struct accepts_iter_enabled : std::false_type {};

template <class It, class ToIndex>
struct accepts_iter_enabled<
    It, ToIndex,
    std::void_t<iter_ref_t<It>,
                std::invoke_result_t<ToIndex &, iter_ref_t<It>>>>
    : std::bool_constant<
          is_input_iterator_v<It> &&
          std::is_invocable_r_v<int, ToIndex &, iter_ref_t<It>>> {};

template <class It, class ToIndex>
inline constexpr bool accepts_iter_enabled_v =
    accepts_iter_enabled<It, ToIndex>::value;

template <class Range, class ToIndex, class = void>
struct accepts_range_enabled : std::false_type {};

template <class Range, class ToIndex>
struct accepts_range_enabled<
    Range, ToIndex, std::void_t<range_begin_t<Range>, range_end_t<Range>>>
    : std::bool_constant<
          std::is_same_v<range_begin_t<Range>, range_end_t<Range>> &&
          accepts_iter_enabled_v<range_begin_t<Range>, ToIndex>> {};

template <class Range, class ToIndex>
inline constexpr bool accepts_range_enabled_v =
    accepts_range_enabled<Range, ToIndex>::value;

template <class T, class = void>
struct is_static_castable_to_int : std::false_type {};

template <class T>
struct is_static_castable_to_int<
    T, std::void_t<decltype(static_cast<int>(std::declval<T>()))>>
    : std::true_type {};

template <class T>
inline constexpr bool is_static_castable_to_int_v =
    is_static_castable_to_int<T>::value;

struct to_int {
    template <class T,
              std::enable_if_t<is_static_castable_to_int_v<T &&>, int> = 0>
    constexpr int operator()(T &&x) const
        noexcept(noexcept(static_cast<int>(std::forward<T>(x)))) {
        return static_cast<int>(std::forward<T>(x));
    }
};

template <class R, class = void>
struct count_accumulator_enabled : std::false_type {};

template <class R>
struct count_accumulator_enabled<
    R, std::void_t<decltype(std::declval<R &>() += std::declval<const R &>())>>
    : std::bool_constant<std::is_constructible_v<R, int> &&
                         std::is_copy_constructible_v<R> &&
                         std::is_assignable_v<R &, const R &>> {};

template <class R>
inline constexpr bool count_accumulator_enabled_v =
    count_accumulator_enabled<R>::value;

template <class R>
inline constexpr bool dense_transition_count_enabled_v =
    count_accumulator_enabled_v<R>;

template <class R>
inline constexpr bool sparse_transition_count_enabled_v =
    count_accumulator_enabled_v<R> &&
    std::is_constructible_v<std::pair<int, R>, int, const R &>;
} // namespace internal

class DFA {
  private:
    int n;
    int sigma;
    int initial_state;

    std::vector<unsigned char> accepting;
    std::vector<std::vector<int>> trans;

    std::string key;

    // initial_state や trans などが範囲外となることも一応許容する

  public:
    DFA(const int n, const int sigma, const int initial_state,
        const std::vector<unsigned char> &accepting,
        const std::vector<std::vector<int>> &trans, const std::string &key)
        : n(n), sigma(sigma), initial_state(initial_state),
          accepting(accepting), trans(trans), key(key) {
        assert(n >= 0);
        assert(sigma >= 0);

        assert(static_cast<int>(accepting.size()) >= n);
        assert(static_cast<int>(trans.size()) >= n);
        for (int i = 0; i < n; i += 1) {
            assert(static_cast<int>(trans[i].size()) >= sigma);
        }
    }

    template <std::size_t N, std::size_t SIGMA>
    DFA(const int initial_state, const std::array<unsigned char, N> &acc,
        const std::array<std::array<int, SIGMA>, N> &tr, const std::string &key)
        : n(N), sigma(SIGMA), initial_state(initial_state),
          accepting(acc.begin(), acc.end()), trans(N, std::vector<int>(SIGMA)),
          key(key) {
        // acc と tr の要素数は決まっている
        for (int i = 0; i < N; i += 1) {
            for (int j = 0; j < SIGMA; j += 1) {
                trans[i][j] = tr[i][j];
            }
        }
    }

    // 状態数
    int state_size() const noexcept { return n; }
    // アルファベット（文字集合）の要素数
    int alphabet_size() const noexcept { return sigma; }
    // 初期状態のインデックス
    int index_of_initial_state() const noexcept { return initial_state; }

    const std::string &get_key() const & noexcept { return key; }

    // src が受理状態かどうか
    bool is_accepting(int src) const {
        if (src < 0 || src >= n) {
            return false;
        }
        return static_cast<bool>(accepting[src]);
    }

    // ラベルが label である文字が入力されたとき
    // src からどの状態に遷移するか
    //
    // src や label が範囲外である場合は -1 を返す
    //
    // -1 などの負の数の返り値が、省略された dead 状態 (sink) を表す可能性がある
    int next(int src, int label) const {
        if (src < 0 || src >= n) {
            return -1;
        }
        if (label < 0 || label >= sigma) {
            return -1;
        }
        return trans[src][label];
    }

    // その文字列が受理されるかどうか
    //
    // to_index: 各文字をラベルに変換する関数
    template <class It, class ToIndex,
              std::enable_if_t<internal::accepts_iter_enabled_v<It, ToIndex>,
                               int> = 0>
    bool accepts(It first, It last, ToIndex to_index) const {
        int cur = initial_state;
        for (; first != last; ++first) {
            if (cur < 0 || cur >= n) {
                return false;
            }
            const int label = std::invoke(to_index, *first);
            if (label < 0 || label >= sigma) {
                return false;
            }
            cur = trans[cur][label];
        }

        // is_accepting 関数側でも cur が範囲内であるかどうかはチェックされる
        return is_accepting(cur);
    }

    // その文字列が受理されるかどうか
    //
    // to_index: 各文字をラベルに変換する関数
    template <
        class Range, class ToIndex,
        std::enable_if_t<
            internal::accepts_range_enabled_v<Range, std::decay_t<ToIndex>> &&
                std::is_constructible_v<std::decay_t<ToIndex>, ToIndex &&>,
            int> = 0>
    bool accepts(const Range &r, ToIndex &&to_index) const {
        using std::begin;
        using std::end;
        using F = std::decay_t<ToIndex>;

        return accepts(begin(r), end(r), F(std::forward<ToIndex>(to_index)));
    }

    // その文字列が受理されるかどうか
    template <
        class It,
        std::enable_if_t<internal::accepts_iter_enabled_v<It, internal::to_int>,
                         int> = 0>
    bool accepts(It first, It last) const {
        return accepts(first, last, internal::to_int{});
    }

    // その文字列が受理されるかどうか
    template <class Range, std::enable_if_t<internal::accepts_range_enabled_v<
                                                Range, internal::to_int>,
                                            int> = 0>
    bool accepts(const Range &r) const {
        return accepts(r, internal::to_int{});
    }

    // [src][dst]: src から dst に遷移する入力文字の個数
    //
    // 返り値の型は atcoder::modint998244353 などにもできる
    //
    // 省略された dead 状態 (sink) がある場合、
    // src ごとの個数の総和が文字集合の要素数に一致しない可能性がある
    template <class R = int,
              std::enable_if_t<internal::dense_transition_count_enabled_v<R>,
                               int> = 0>
    std::vector<std::vector<R>> dense_transition_count_matrix() const {
        const R zero(0);
        const R one(1);

        std::vector<std::vector<R>> res(n, std::vector<R>(n, zero));
        for (int src = 0; src < n; src += 1) {
            for (int label = 0; label < sigma; label += 1) {
                int dst = trans[src][label];
                if (dst >= 0 && dst < n) {
                    res[src][dst] += one;
                }
            }
        }

        return res;
    }

    // [src]:
    // src から dst に遷移する入力文字が存在する dst についての
    // (dst, src から dst に遷移する入力文字の個数) の vector
    //
    // src ごとに格納される dst は相異なるが、昇順であることは保証されない
    // （適宜、ソートする必要がある）
    //
    // 返り値の個数の型は atcoder::modint998244353 などにもできる
    //
    // 省略された dead 状態 (sink) がある場合、
    // src ごとの個数の総和が文字集合の要素数に一致しない可能性がある
    template <class R = int,
              std::enable_if_t<internal::sparse_transition_count_enabled_v<R>,
                               int> = 0>
    std::vector<std::vector<std::pair<int, R>>>
    sparse_transition_count_matrix() const {
        const R zero(0);
        const R one(1);

        std::vector<std::vector<std::pair<int, R>>> res(
            n, std::vector<std::pair<int, R>>());

        // 個数の型が atcoder::modint998244353 などの場合、
        // 値が 0 と等しいことと、入力文字が存在しないことは
        // 同値ではない
        std::vector<R> cnt(n, zero);
        std::vector<unsigned char> exists(n, static_cast<unsigned char>(false));

        std::vector<int> dsts;
        dsts.reserve(n);
        for (int src = 0; src < n; src += 1) {
            for (int label = 0; label < sigma; label += 1) {
                int dst = trans[src][label];
                if (dst >= 0 && dst < n) {
                    cnt[dst] += one;
                    if (!static_cast<bool>(exists[dst])) {
                        exists[dst] = static_cast<unsigned char>(true);
                        dsts.emplace_back(dst);
                    }
                }
            }

            res[src].reserve(dsts.size());
            for (int dst : dsts) {
                res[src].emplace_back(dst, cnt[dst]);
                cnt[dst] = zero;
                exists[dst] = static_cast<unsigned char>(false);
            }

            dsts.clear();
        }

        return res;
    }

    // 空でない部分文字列のうち、受理されるものの長さの最大値
    //
    // 受理される空でない部分文字列が存在しなければ -1 を返す
    //
    // 空文字列も含んで考えたい場合も、空文字列が受理されるかどうかを別で求めればよい
    //
    // to_index: 各文字をラベルに変換する関数
    template <class It, class ToIndex,
              std::enable_if_t<internal::accepts_iter_enabled_v<It, ToIndex>,
                               int> = 0>
    int longest_accepted_substring_length(It first, It last,
                                          ToIndex to_index) const {
        int ans = -1;

        std::vector<int> dp_table(n, -1), next_table(n, -1);
        for (; first != last; ++first) {
            const int label = std::invoke(to_index, *first);
            std::fill(next_table.begin(), next_table.end(), -1);

            if (label >= 0 && label < sigma) {
                {
                    // 長さ 1
                    int next_state = next(initial_state, label);
                    if (next_state >= 0 && next_state < n) {
                        next_table[next_state] = 1;
                    }
                }

                for (int i = 0; i < n; i += 1) {
                    // 長さ 2 以上
                    if (dp_table[i] > 0) {
                        int next_state = next(i, label);
                        if (next_state >= 0 && next_state < n) {
                            int cand = dp_table[i] + 1;
                            if (next_table[next_state] < cand) {
                                next_table[next_state] = cand;
                            }
                        }
                    }
                }
            }

            dp_table.swap(next_table);

            for (int i = 0; i < n; i += 1) {
                if (is_accepting(i)) {
                    if (ans < dp_table[i]) {
                        ans = dp_table[i];
                    }
                }
            }
        }

        return ans;
    }

    // 空でない部分文字列のうち、受理されるものの長さの最大値
    //
    // 受理される空でない部分文字列が存在しなければ -1 を返す
    //
    // 空文字列も含んで考えたい場合も、空文字列が受理されるかどうかを別で求めればよい
    //
    // to_index: 各文字をラベルに変換する関数
    template <
        class Range, class ToIndex,
        std::enable_if_t<
            internal::accepts_range_enabled_v<Range, std::decay_t<ToIndex>> &&
                std::is_constructible_v<std::decay_t<ToIndex>, ToIndex &&>,
            int> = 0>
    int longest_accepted_substring_length(const Range &r,
                                          ToIndex &&to_index) const {
        using std::begin;
        using std::end;
        using F = std::decay_t<ToIndex>;

        return longest_accepted_substring_length(
            begin(r), end(r), F(std::forward<ToIndex>(to_index)));
    }

    // 空でない部分文字列のうち、受理されるものの長さの最大値
    //
    // 受理される空でない部分文字列が存在しなければ -1 を返す
    //
    // 空文字列も含んで考えたい場合も、空文字列が受理されるかどうかを別で求めればよい
    template <
        class It,
        std::enable_if_t<internal::accepts_iter_enabled_v<It, internal::to_int>,
                         int> = 0>
    int longest_accepted_substring_length(It first, It last) const {
        return longest_accepted_substring_length(first, last,
                                                 internal::to_int{});
    }

    // 空でない部分文字列のうち、受理されるものの長さの最大値
    //
    // 受理される空でない部分文字列が存在しなければ -1 を返す
    //
    // 空文字列も含んで考えたい場合も、空文字列が受理されるかどうかを別で求めればよい
    template <class Range, std::enable_if_t<internal::accepts_range_enabled_v<
                                                Range, internal::to_int>,
                                            int> = 0>
    int longest_accepted_substring_length(const Range &r) const {
        return longest_accepted_substring_length(r, internal::to_int{});
    }

    // 空でない部分文字列のうち、受理されるものの個数
    //
    // 空文字列も含んで考えたい場合も、空文字列が受理されるかどうかを別で求めればよい
    //
    // 返り値の型は atcoder::modint998244353 などにもできる
    //
    // to_index: 各文字をラベルに変換する関数
    template <class R = long long, class It, class ToIndex,
              std::enable_if_t<internal::accepts_iter_enabled_v<It, ToIndex> &&
                                   internal::count_accumulator_enabled_v<R>,
                               int> = 0>
    R count_accepted_substrings(It first, It last, ToIndex to_index) const {
        const R zero(0);
        const R one(1);

        R ans = zero;
        std::vector<R> dp_table(n, zero), next_table(n, zero);

        for (; first != last; ++first) {
            const int label = std::invoke(to_index, *first);
            std::fill(next_table.begin(), next_table.end(), zero);

            if (label >= 0 && label < sigma) {
                {
                    // 長さ 1
                    int next_state = next(initial_state, label);
                    if (next_state >= 0 && next_state < n) {
                        next_table[next_state] += one;
                    }
                }

                for (int i = 0; i < n; i += 1) {
                    // 長さ 2 以上
                    int next_state = next(i, label);
                    if (next_state >= 0 && next_state < n) {
                        next_table[next_state] += dp_table[i];
                    }
                }
            }

            dp_table.swap(next_table);

            for (int i = 0; i < n; i += 1) {
                if (is_accepting(i)) {
                    ans += dp_table[i];
                }
            }
        }

        return ans;
    }

    // 空でない部分文字列のうち、受理されるものの個数
    //
    // 空文字列も含んで考えたい場合も、空文字列が受理されるかどうかを別で求めればよい
    //
    // 返り値の型は atcoder::modint998244353 などにもできる
    //
    // to_index: 各文字をラベルに変換する関数
    template <
        class R = long long, class Range, class ToIndex,
        std::enable_if_t<
            internal::accepts_range_enabled_v<Range, std::decay_t<ToIndex>> &&
                std::is_constructible_v<std::decay_t<ToIndex>, ToIndex &&> &&
                internal::count_accumulator_enabled_v<R>,
            int> = 0>
    R count_accepted_substrings(const Range &r, ToIndex &&to_index) const {
        using std::begin;
        using std::end;
        using F = std::decay_t<ToIndex>;

        return count_accepted_substrings<R>(begin(r), end(r),
                                            F(std::forward<ToIndex>(to_index)));
    }

    // 空でない部分文字列のうち、受理されるものの個数
    //
    // 空文字列も含んで考えたい場合も、空文字列が受理されるかどうかを別で求めればよい
    //
    // 返り値の型は atcoder::modint998244353 などにもできる
    template <class R = long long, class It,
              std::enable_if_t<
                  internal::accepts_iter_enabled_v<It, internal::to_int> &&
                      internal::count_accumulator_enabled_v<R>,
                  int> = 0>
    R count_accepted_substrings(It first, It last) const {
        return count_accepted_substrings<R>(first, last, internal::to_int{});
    }

    // 空でない部分文字列のうち、受理されるものの個数
    //
    // 空文字列も含んで考えたい場合も、空文字列が受理されるかどうかを別で求めればよい
    //
    // 返り値の型は atcoder::modint998244353 などにもできる
    template <class R = long long, class Range,
              std::enable_if_t<
                  internal::accepts_range_enabled_v<Range, internal::to_int> &&
                      internal::count_accumulator_enabled_v<R>,
                  int> = 0>
    R count_accepted_substrings(const Range &r) const {
        return count_accepted_substrings<R>(r, internal::to_int{});
    }
};

class DFAs {
  private:
    std::vector<DFA> dfas;

  public:
    const std::vector<DFA> &operator()() const & noexcept { return dfas; }

    // キーが key である DFA のインデックスを返す
    //
    // 存在しなければ -1 を返す
    int index_of(const std::string &key) const {
        auto it = std::find_if(
            dfas.begin(), dfas.end(),
            [&key](const DFA &dfa) -> bool { return dfa.get_key() == key; });
        if (it != dfas.end()) {
            return static_cast<int>(it - dfas.begin());
        } else {
            return -1;
        }
    }

    // キーが key である DFA を返す
    //
    // 存在しなければ abort することに注意
    const DFA &get(const std::string &key) const & {
        int i = index_of(key);
        if (i < 0) {
            std::abort();
        }
        return dfas[i];
    }

    // DFA を登録する
    //
    // 既に同じキーの DFA が存在すれば abort することに注意
    template <std::size_t N, std::size_t SIGMA>
    void register_dfa(const int initial_state,
                      const std::array<unsigned char, N> &acc,
                      const std::array<std::array<int, SIGMA>, N> &tr,
                      const std::string &key) {
        DFA dfa(initial_state, acc, tr, key);

        int i = index_of(key);
        if (i >= 0) {
            std::abort(); // already exists
        }
        dfas.emplace_back(dfa);
    }
};

inline DFAs &dfas() {
    static DFAs dfas;
    return dfas;
}
} // namespace learned_dfa

#include <array>

namespace learned_dfa_2 {
// States: 4, Alphabet: 4
// Symbol index mapping:
//   0: 0
//   1: 1
//   2: 2
//   3: 3

inline constexpr int N = 4;
inline constexpr int SIGMA = 4;
inline constexpr int INITIAL_STATE = 0;

inline constexpr std::array<unsigned char, N> ACCEPTING = {{0, 1, 0, 1}};

inline constexpr std::array<std::array<int, SIGMA>, N> TRANS = {{
    {{2, 0, 2, 1}},
    {{2, 0, 3, 1}},
    {{2, 2, 2, 2}},
    {{2, 2, 3, 1}},
}};

static const int __learned_dfa_register_2 = [] {
    learned_dfa::dfas().register_dfa(INITIAL_STATE, ACCEPTING, TRANS, "2");
    return 0;
}();
} // namespace learned_dfa_2

#include <array>

namespace learned_dfa_3 {
// States: 8, Alphabet: 8
// Symbol index mapping:
//   0: 0
//   1: 1
//   2: 2
//   3: 3
//   4: 4
//   5: 5
//   6: 6
//   7: 7

inline constexpr int N = 8;
inline constexpr int SIGMA = 8;
inline constexpr int INITIAL_STATE = 0;

inline constexpr std::array<unsigned char, N> ACCEPTING = {
    {0, 1, 0, 0, 1, 0, 1, 1}};

inline constexpr std::array<std::array<int, SIGMA>, N> TRANS = {{
    {{2, 0, 2, 5, 2, 0, 2, 1}},
    {{2, 0, 3, 5, 4, 6, 7, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2}},
    {{2, 2, 3, 5, 2, 2, 7, 1}},
    {{2, 2, 2, 2, 4, 4, 7, 1}},
    {{2, 0, 3, 5, 2, 0, 7, 1}},
    {{2, 0, 2, 5, 4, 6, 7, 1}},
    {{2, 2, 3, 5, 4, 4, 7, 1}},
}};

static const int __learned_dfa_register_3 = [] {
    learned_dfa::dfas().register_dfa(INITIAL_STATE, ACCEPTING, TRANS, "3");
    return 0;
}();
} // namespace learned_dfa_3

#include <array>

namespace learned_dfa_4 {
// States: 16, Alphabet: 16
// Symbol index mapping:
//   0: 0
//   1: 1
//   2: 2
//   3: 3
//   4: 4
//   5: 5
//   6: 6
//   7: 7
//   8: 8
//   9: 9
//   10: 10
//   11: 11
//   12: 12
//   13: 13
//   14: 14
//   15: 15

inline constexpr int N = 16;
inline constexpr int SIGMA = 16;
inline constexpr int INITIAL_STATE = 0;

inline constexpr std::array<unsigned char, N> ACCEPTING = {
    {0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1}};

inline constexpr std::array<std::array<int, SIGMA>, N> TRANS = {{
    {{2, 0, 2, 5, 2, 0, 2, 9, 2, 0, 2, 5, 2, 0, 2, 1}},
    {{2, 0, 3, 5, 6, 10, 11, 9, 4, 7, 8, 12, 13, 14, 15, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2}},
    {{2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 3, 5, 2, 2, 15, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2, 4, 4, 4, 4, 13, 13, 15, 1}},
    {{2, 0, 3, 5, 2, 0, 11, 9, 2, 0, 3, 5, 2, 0, 15, 1}},
    {{2, 2, 2, 2, 6, 6, 11, 9, 2, 2, 2, 2, 13, 13, 15, 1}},
    {{2, 0, 2, 5, 2, 0, 2, 9, 4, 7, 4, 12, 13, 14, 15, 1}},
    {{2, 2, 3, 5, 2, 2, 11, 9, 4, 4, 8, 12, 13, 13, 15, 1}},
    {{2, 0, 3, 5, 6, 10, 11, 9, 2, 0, 3, 5, 13, 14, 15, 1}},
    {{2, 0, 2, 5, 6, 10, 11, 9, 2, 0, 2, 5, 13, 14, 15, 1}},
    {{2, 2, 3, 5, 6, 6, 11, 9, 2, 2, 3, 5, 13, 13, 15, 1}},
    {{2, 0, 3, 5, 2, 0, 11, 9, 4, 7, 8, 12, 13, 14, 15, 1}},
    {{2, 2, 2, 2, 6, 6, 11, 9, 4, 4, 4, 4, 13, 13, 15, 1}},
    {{2, 0, 2, 5, 6, 10, 11, 9, 4, 7, 4, 12, 13, 14, 15, 1}},
    {{2, 2, 3, 5, 6, 6, 11, 9, 4, 4, 8, 12, 13, 13, 15, 1}},
}};

static const int __learned_dfa_register_4 = [] {
    learned_dfa::dfas().register_dfa(INITIAL_STATE, ACCEPTING, TRANS, "4");
    return 0;
}();
} // namespace learned_dfa_4

#include <array>

namespace learned_dfa_5 {
// States: 34, Alphabet: 32
// Symbol index mapping:
//   0: 0
//   1: 1
//   2: 2
//   3: 3
//   4: 4
//   5: 5
//   6: 6
//   7: 7
//   8: 8
//   9: 9
//   10: 10
//   11: 11
//   12: 12
//   13: 13
//   14: 14
//   15: 15
//   16: 16
//   17: 17
//   18: 18
//   19: 19
//   20: 20
//   21: 21
//   22: 22
//   23: 23
//   24: 24
//   25: 25
//   26: 26
//   27: 27
//   28: 28
//   29: 29
//   30: 30
//   31: 31

inline constexpr int N = 34;
inline constexpr int SIGMA = 32;
inline constexpr int INITIAL_STATE = 0;

inline constexpr std::array<unsigned char, N> ACCEPTING = {
    {0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1,
     0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0}};

inline constexpr std::array<std::array<int, SIGMA>, N> TRANS = {{
    {{2, 0, 2, 5, 2, 0, 2, 9, 2, 0, 2, 5, 2, 0,  2, 17,
      2, 0, 2, 5, 2, 0, 2, 9, 2, 0, 2, 5, 2, 33, 2, 1}},
    {{2, 0, 3, 5,  6,  10, 11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      4, 7, 8, 13, 14, 15, 16, 24, 25, 26, 27, 28, 29, 30, 31, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
      2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2}},
    {{2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 3, 5, 2, 2, 23, 17,
      2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 3, 5, 2, 2, 31, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2,  2,  2,  2,  2,  2,  2,  2,  2,
      4, 4, 4, 4, 4, 4, 4, 32, 25, 25, 25, 25, 29, 29, 31, 1}},
    {{2, 0, 3, 5, 2, 0, 11, 9, 2, 0, 3, 5, 2, 0,  23, 17,
      2, 0, 3, 5, 2, 0, 11, 9, 2, 0, 3, 5, 2, 33, 31, 1}},
    {{2, 2, 2, 2, 6, 6, 11, 9, 2, 2, 2, 2, 21, 21, 23, 17,
      2, 2, 2, 2, 6, 6, 11, 9, 2, 2, 2, 2, 29, 29, 31, 1}},
    {{2, 0, 2, 5,  2, 0, 2, 9,  2,  0,  2,  5,  2,  0,  2,  17,
      4, 7, 4, 13, 4, 7, 4, 24, 25, 26, 25, 28, 29, 30, 31, 1}},
    {{2, 2, 3, 5,  2, 2, 11, 9,  2,  2,  3,  5,  2,  2,  23, 17,
      4, 4, 8, 13, 4, 4, 16, 24, 25, 25, 27, 28, 29, 29, 31, 1}},
    {{2, 0, 3, 5, 6, 10, 11, 9, 2, 0, 3, 5, 21, 22, 23, 17,
      2, 0, 3, 5, 6, 10, 11, 9, 2, 0, 3, 5, 29, 30, 31, 1}},
    {{2, 0, 2, 5, 6, 10, 11, 9, 2, 0, 2, 5, 21, 22, 23, 17,
      2, 0, 2, 5, 6, 10, 11, 9, 2, 0, 2, 5, 29, 30, 31, 1}},
    {{2, 2, 3, 5, 6, 6, 11, 9, 2, 2, 3, 5, 21, 21, 23, 17,
      2, 2, 3, 5, 6, 6, 11, 9, 2, 2, 3, 5, 29, 29, 31, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2, 12, 12, 12, 12, 21, 21, 23, 17,
      2, 2, 2, 2, 2, 2, 2, 2, 25, 25, 25, 25, 29, 29, 31, 1}},
    {{2, 0, 3, 5,  2, 0, 11, 9,  2,  0,  3,  5,  2,  0,  23, 17,
      4, 7, 8, 13, 4, 7, 16, 24, 25, 26, 27, 28, 29, 30, 31, 1}},
    {{2, 2, 2, 2, 6,  6,  11, 9,  2,  2,  2,  2,  21, 21, 23, 17,
      4, 4, 4, 4, 14, 14, 16, 24, 25, 25, 25, 25, 29, 29, 31, 1}},
    {{2, 0, 2, 5,  6,  10, 11, 9,  2,  0,  2,  5,  21, 22, 23, 17,
      4, 7, 4, 13, 14, 15, 16, 24, 25, 26, 25, 28, 29, 30, 31, 1}},
    {{2, 2, 3, 5,  6,  6,  11, 9,  2,  2,  3,  5,  21, 21, 23, 17,
      4, 4, 8, 13, 14, 14, 16, 24, 25, 25, 27, 28, 29, 29, 31, 1}},
    {{2, 0, 3, 5, 6, 10, 11, 9, 12, 18, 19, 20, 21, 22, 23, 17,
      2, 0, 3, 5, 6, 10, 11, 9, 25, 26, 27, 28, 29, 30, 31, 1}},
    {{2, 0, 2, 5, 2, 0, 2, 9, 12, 18, 12, 20, 21, 22, 23, 17,
      2, 0, 2, 5, 2, 0, 2, 9, 25, 26, 25, 28, 29, 30, 31, 1}},
    {{2, 2, 3, 5, 2, 2, 11, 9, 12, 12, 19, 20, 21, 21, 23, 17,
      2, 2, 3, 5, 2, 2, 11, 9, 25, 25, 27, 28, 29, 29, 31, 1}},
    {{2, 0, 3, 5, 2, 0, 11, 9, 12, 18, 19, 20, 21, 22, 23, 17,
      2, 0, 3, 5, 2, 0, 11, 9, 25, 26, 27, 28, 29, 30, 31, 1}},
    {{2, 2, 2, 2, 6, 6, 11, 9, 12, 12, 12, 12, 21, 21, 23, 17,
      2, 2, 2, 2, 6, 6, 11, 9, 25, 25, 25, 25, 29, 29, 31, 1}},
    {{2, 0, 2, 5, 6, 10, 11, 9, 12, 18, 12, 20, 21, 22, 23, 17,
      2, 0, 2, 5, 6, 10, 11, 9, 25, 26, 25, 28, 29, 30, 31, 1}},
    {{2, 2, 3, 5, 6, 6, 11, 9, 12, 12, 19, 20, 21, 21, 23, 17,
      2, 2, 3, 5, 6, 6, 11, 9, 25, 25, 27, 28, 29, 29, 31, 1}},
    {{2, 0, 3, 5,  6,  10, 11, 9,  2,  0,  3,  5,  21, 22, 23, 17,
      4, 7, 8, 13, 14, 15, 16, 24, 25, 26, 27, 28, 29, 30, 31, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2,  12, 12, 12, 12, 21, 21, 23, 17,
      4, 4, 4, 4, 4, 4, 4, 32, 25, 25, 25, 25, 29, 29, 31, 1}},
    {{2, 0, 2, 5,  2, 0, 2, 9,  12, 18, 12, 20, 21, 22, 23, 17,
      4, 7, 4, 13, 4, 7, 4, 24, 25, 26, 25, 28, 29, 30, 31, 1}},
    {{2, 2, 3, 5,  2, 2, 11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      4, 4, 8, 13, 4, 4, 16, 24, 25, 25, 27, 28, 29, 29, 31, 1}},
    {{2, 0, 3, 5,  2, 0, 11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      4, 7, 8, 13, 4, 7, 16, 24, 25, 26, 27, 28, 29, 30, 31, 1}},
    {{2, 2, 2, 2, 6,  6,  11, 9,  12, 12, 12, 12, 21, 21, 23, 17,
      4, 4, 4, 4, 14, 14, 16, 24, 25, 25, 25, 25, 29, 29, 31, 1}},
    {{2, 0, 2, 5,  6,  10, 11, 9,  12, 18, 12, 20, 21, 22, 23, 17,
      4, 7, 4, 13, 14, 15, 16, 24, 25, 26, 25, 28, 29, 30, 31, 1}},
    {{2, 2, 3, 5,  6,  6,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      4, 4, 8, 13, 14, 14, 16, 24, 25, 25, 27, 28, 29, 29, 31, 1}},
    {{2, 2, 2, 2, 2, 2,  2, 2,  2,  2,  2,  2,  2,  2,  2,  2,
      4, 4, 4, 4, 4, 32, 4, 32, 25, 25, 25, 25, 29, 30, 31, 1}},
    {{2, 0, 2, 5, 2, 0,  2, 9,  2, 0, 2, 5, 2, 0,  2, 17,
      2, 0, 2, 5, 2, 33, 2, 24, 2, 0, 2, 5, 2, 33, 2, 1}},
}};

static const int __learned_dfa_register_5 = [] {
    learned_dfa::dfas().register_dfa(INITIAL_STATE, ACCEPTING, TRANS, "5");
    return 0;
}();
} // namespace learned_dfa_5

#include <array>

namespace learned_dfa_6 {
// States: 80, Alphabet: 64
// Symbol index mapping:
//   0: 0
//   1: 1
//   2: 2
//   3: 3
//   4: 4
//   5: 5
//   6: 6
//   7: 7
//   8: 8
//   9: 9
//   10: 10
//   11: 11
//   12: 12
//   13: 13
//   14: 14
//   15: 15
//   16: 16
//   17: 17
//   18: 18
//   19: 19
//   20: 20
//   21: 21
//   22: 22
//   23: 23
//   24: 24
//   25: 25
//   26: 26
//   27: 27
//   28: 28
//   29: 29
//   30: 30
//   31: 31
//   32: 32
//   33: 33
//   34: 34
//   35: 35
//   36: 36
//   37: 37
//   38: 38
//   39: 39
//   40: 40
//   41: 41
//   42: 42
//   43: 43
//   44: 44
//   45: 45
//   46: 46
//   47: 47
//   48: 48
//   49: 49
//   50: 50
//   51: 51
//   52: 52
//   53: 53
//   54: 54
//   55: 55
//   56: 56
//   57: 57
//   58: 58
//   59: 59
//   60: 60
//   61: 61
//   62: 62
//   63: 63

inline constexpr int N = 80;
inline constexpr int SIGMA = 64;
inline constexpr int INITIAL_STATE = 0;

inline constexpr std::array<unsigned char, N> ACCEPTING = {
    {0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0,
     0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0,
     0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
     1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0}};

inline constexpr std::array<std::array<int, SIGMA>, N> TRANS = {{
    {{2, 0, 2, 5,  2, 0, 2, 9,  2, 0,  2, 5, 2, 0,  2, 17, 2, 0,  2, 5, 2, 0,
      2, 9, 2, 0,  2, 5, 2, 66, 2, 33, 2, 0, 2, 5,  2, 0,  2, 9,  2, 0, 2, 5,
      2, 0, 2, 17, 2, 0, 2, 5,  2, 0,  2, 9, 2, 75, 2, 76, 2, 73, 2, 1}},
    {{2,  0,  3,  5,  6,  10, 11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      24, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 33,
      4,  7,  8,  13, 14, 15, 16, 25, 26, 27, 28, 29, 30, 31, 32, 48,
      49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
      2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
      2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2}},
    {{2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 3,  5,  2, 2, 23, 17,
      2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 3,  5,  2, 2, 47, 33,
      2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 3,  5,  2, 2, 23, 17,
      2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 77, 76, 2, 2, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      4,  4,  4,  4,  4,  4,  4,  67, 4,  4,  4,  4,  4,  4,  70, 68,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2, 0, 3, 5, 2, 0, 11, 9, 2, 0,  3,  5,  2, 0,  23, 17,
      2, 0, 3, 5, 2, 0, 11, 9, 2, 0,  3,  5,  2, 66, 47, 33,
      2, 0, 3, 5, 2, 0, 11, 9, 2, 0,  3,  5,  2, 0,  23, 17,
      2, 0, 3, 5, 2, 0, 11, 9, 2, 75, 77, 76, 2, 73, 63, 1}},
    {{2, 2, 2, 2, 6, 6, 11, 9, 2, 2, 2, 2, 21, 21, 23, 17,
      2, 2, 2, 2, 6, 6, 11, 9, 2, 2, 2, 2, 45, 45, 47, 33,
      2, 2, 2, 2, 6, 6, 11, 9, 2, 2, 2, 2, 21, 21, 23, 17,
      2, 2, 2, 2, 6, 6, 11, 9, 2, 2, 2, 2, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  2,  0,  2,  9,  2,  0,  2,  5,  2,  0,  2,  17,
      2,  0,  2,  5,  2,  0,  2,  9,  2,  0,  2,  5,  2,  66, 2,  33,
      4,  7,  4,  13, 4,  7,  4,  25, 4,  7,  4,  13, 4,  7,  70, 48,
      49, 50, 49, 52, 49, 50, 49, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  2,  2,  11, 9,  2,  2,  3,  5,  2,  2,  23, 17,
      2,  2,  3,  5,  2,  2,  11, 9,  2,  2,  3,  5,  2,  2,  47, 33,
      4,  4,  8,  13, 4,  4,  16, 25, 4,  4,  8,  13, 4,  4,  32, 48,
      49, 49, 51, 52, 49, 49, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2, 0, 3, 5, 6, 10, 11, 9, 2, 0,  3,  5,  21, 22, 23, 17,
      2, 0, 3, 5, 6, 10, 11, 9, 2, 0,  3,  5,  45, 46, 47, 33,
      2, 0, 3, 5, 6, 10, 11, 9, 2, 0,  3,  5,  21, 22, 23, 17,
      2, 0, 3, 5, 6, 10, 11, 9, 2, 75, 77, 76, 61, 62, 63, 1}},
    {{2, 0, 2, 5, 6, 10, 11, 9, 2, 0,  2, 5,  21, 22, 23, 17,
      2, 0, 2, 5, 6, 10, 11, 9, 2, 0,  2, 5,  45, 46, 47, 33,
      2, 0, 2, 5, 6, 10, 11, 9, 2, 0,  2, 5,  21, 22, 23, 17,
      2, 0, 2, 5, 6, 10, 11, 9, 2, 75, 2, 76, 61, 62, 63, 1}},
    {{2, 2, 3, 5, 6, 6, 11, 9, 2, 2, 3,  5,  21, 21, 23, 17,
      2, 2, 3, 5, 6, 6, 11, 9, 2, 2, 3,  5,  45, 45, 47, 33,
      2, 2, 3, 5, 6, 6, 11, 9, 2, 2, 3,  5,  21, 21, 23, 17,
      2, 2, 3, 5, 6, 6, 11, 9, 2, 2, 77, 76, 61, 61, 63, 1}},
    {{2, 2, 2, 2, 2, 2, 2, 2, 12, 12, 12, 12, 21, 21, 23, 17,
      2, 2, 2, 2, 2, 2, 2, 2, 41, 41, 41, 41, 45, 45, 47, 33,
      2, 2, 2, 2, 2, 2, 2, 2, 12, 12, 12, 12, 21, 21, 23, 17,
      2, 2, 2, 2, 2, 2, 2, 2, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  2,  0,  11, 9,  2,  0,  3,  5,  2,  0,  23, 17,
      2,  0,  3,  5,  2,  0,  11, 9,  2,  0,  3,  5,  2,  66, 47, 33,
      4,  7,  8,  13, 4,  7,  16, 25, 4,  7,  8,  13, 4,  7,  32, 48,
      49, 50, 51, 52, 49, 50, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  6,  6,  11, 9,  2,  2,  2,  2,  21, 21, 23, 17,
      2,  2,  2,  2,  6,  6,  11, 9,  2,  2,  2,  2,  45, 45, 47, 33,
      4,  4,  4,  4,  14, 14, 16, 25, 4,  4,  4,  4,  30, 30, 32, 48,
      49, 49, 49, 49, 53, 53, 55, 56, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  6,  10, 11, 9,  2,  0,  2,  5,  21, 22, 23, 17,
      2,  0,  2,  5,  6,  10, 11, 9,  2,  0,  2,  5,  45, 46, 47, 33,
      4,  7,  4,  13, 14, 15, 16, 25, 4,  7,  4,  13, 30, 31, 32, 48,
      49, 50, 49, 52, 53, 54, 55, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  6,  6,  11, 9,  2,  2,  3,  5,  21, 21, 23, 17,
      2,  2,  3,  5,  6,  6,  11, 9,  2,  2,  3,  5,  45, 45, 47, 33,
      4,  4,  8,  13, 14, 14, 16, 25, 4,  4,  8,  13, 30, 30, 32, 48,
      49, 49, 51, 52, 53, 53, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2, 0, 3, 5, 6, 10, 11, 9, 12, 18, 19, 20, 21, 22, 23, 17,
      2, 0, 3, 5, 6, 10, 11, 9, 41, 42, 43, 44, 45, 46, 47, 33,
      2, 0, 3, 5, 6, 10, 11, 9, 12, 18, 19, 20, 21, 22, 23, 17,
      2, 0, 3, 5, 6, 10, 11, 9, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2, 0, 2, 5, 2, 0, 2, 9, 12, 18, 12, 20, 21, 22, 23, 17,
      2, 0, 2, 5, 2, 0, 2, 9, 41, 42, 41, 44, 45, 46, 47, 33,
      2, 0, 2, 5, 2, 0, 2, 9, 12, 18, 12, 20, 21, 22, 23, 17,
      2, 0, 2, 5, 2, 0, 2, 9, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2, 2, 3, 5, 2, 2, 11, 9, 12, 12, 19, 20, 21, 21, 23, 17,
      2, 2, 3, 5, 2, 2, 11, 9, 41, 41, 43, 44, 45, 45, 47, 33,
      2, 2, 3, 5, 2, 2, 11, 9, 12, 12, 19, 20, 21, 21, 23, 17,
      2, 2, 3, 5, 2, 2, 11, 9, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2, 0, 3, 5, 2, 0, 11, 9, 12, 18, 19, 20, 21, 22, 23, 17,
      2, 0, 3, 5, 2, 0, 11, 9, 41, 42, 43, 44, 45, 46, 47, 33,
      2, 0, 3, 5, 2, 0, 11, 9, 12, 18, 19, 20, 21, 22, 23, 17,
      2, 0, 3, 5, 2, 0, 11, 9, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2, 2, 2, 2, 6, 6, 11, 9, 12, 12, 12, 12, 21, 21, 23, 17,
      2, 2, 2, 2, 6, 6, 11, 9, 41, 41, 41, 41, 45, 45, 47, 33,
      2, 2, 2, 2, 6, 6, 11, 9, 12, 12, 12, 12, 21, 21, 23, 17,
      2, 2, 2, 2, 6, 6, 11, 9, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2, 0, 2, 5, 6, 10, 11, 9, 12, 18, 12, 20, 21, 22, 23, 17,
      2, 0, 2, 5, 6, 10, 11, 9, 41, 42, 41, 44, 45, 46, 47, 33,
      2, 0, 2, 5, 6, 10, 11, 9, 12, 18, 12, 20, 21, 22, 23, 17,
      2, 0, 2, 5, 6, 10, 11, 9, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2, 2, 3, 5, 6, 6, 11, 9, 12, 12, 19, 20, 21, 21, 23, 17,
      2, 2, 3, 5, 6, 6, 11, 9, 41, 41, 43, 44, 45, 45, 47, 33,
      2, 2, 3, 5, 6, 6, 11, 9, 12, 12, 19, 20, 21, 21, 23, 17,
      2, 2, 3, 5, 6, 6, 11, 9, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      24, 24, 24, 24, 24, 24, 24, 65, 41, 41, 41, 41, 45, 45, 47, 33,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  6,  10, 11, 9,  2,  0,  3,  5,  21, 22, 23, 17,
      2,  0,  3,  5,  6,  10, 11, 9,  2,  0,  3,  5,  45, 46, 47, 33,
      4,  7,  8,  13, 14, 15, 16, 25, 4,  7,  8,  13, 30, 31, 32, 48,
      49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  12, 12, 12, 12, 21, 21, 23, 17,
      2,  2,  2,  2,  2,  2,  2,  2,  41, 41, 41, 41, 45, 45, 47, 33,
      4,  4,  4,  4,  4,  4,  4,  67, 26, 26, 26, 26, 30, 30, 32, 48,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  2,  0,  2,  9,  12, 18, 12, 20, 21, 22, 23, 17,
      2,  0,  2,  5,  2,  0,  2,  9,  41, 42, 41, 44, 45, 46, 47, 33,
      4,  7,  4,  13, 4,  7,  4,  25, 26, 27, 26, 29, 30, 31, 32, 48,
      49, 50, 49, 52, 49, 50, 49, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  2,  2,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      2,  2,  3,  5,  2,  2,  11, 9,  41, 41, 43, 44, 45, 45, 47, 33,
      4,  4,  8,  13, 4,  4,  16, 25, 26, 26, 28, 29, 30, 30, 32, 48,
      49, 49, 51, 52, 49, 49, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  2,  0,  11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      2,  0,  3,  5,  2,  0,  11, 9,  41, 42, 43, 44, 45, 46, 47, 33,
      4,  7,  8,  13, 4,  7,  16, 25, 26, 27, 28, 29, 30, 31, 32, 48,
      49, 50, 51, 52, 49, 50, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  6,  6,  11, 9,  12, 12, 12, 12, 21, 21, 23, 17,
      2,  2,  2,  2,  6,  6,  11, 9,  41, 41, 41, 41, 45, 45, 47, 33,
      4,  4,  4,  4,  14, 14, 16, 25, 26, 26, 26, 26, 30, 30, 32, 48,
      49, 49, 49, 49, 53, 53, 55, 56, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  6,  10, 11, 9,  12, 18, 12, 20, 21, 22, 23, 17,
      2,  0,  2,  5,  6,  10, 11, 9,  41, 42, 41, 44, 45, 46, 47, 33,
      4,  7,  4,  13, 14, 15, 16, 25, 26, 27, 26, 29, 30, 31, 32, 48,
      49, 50, 49, 52, 53, 54, 55, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  6,  6,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      2,  2,  3,  5,  6,  6,  11, 9,  41, 41, 43, 44, 45, 45, 47, 33,
      4,  4,  8,  13, 14, 14, 16, 25, 26, 26, 28, 29, 30, 30, 32, 48,
      49, 49, 51, 52, 53, 53, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  6,  10, 11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      24, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 33,
      2,  0,  3,  5,  6,  10, 11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  0,  2,  5,  2,  0,  2,  9,  2,  0,  2,  5,  2,  0,  2,  17,
      24, 34, 24, 36, 24, 34, 24, 40, 41, 42, 41, 44, 45, 46, 47, 33,
      2,  0,  2,  5,  2,  0,  2,  9,  2,  0,  2,  5,  2,  0,  2,  17,
      49, 50, 49, 52, 49, 50, 49, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  2,  2,  11, 9,  2,  2,  3,  5,  2,  2,  23, 17,
      24, 24, 35, 36, 24, 24, 39, 40, 41, 41, 43, 44, 45, 45, 47, 33,
      2,  2,  3,  5,  2,  2,  11, 9,  2,  2,  3,  5,  2,  2,  23, 17,
      49, 49, 51, 52, 49, 49, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  2,  0,  11, 9,  2,  0,  3,  5,  2,  0,  23, 17,
      24, 34, 35, 36, 24, 34, 39, 40, 41, 42, 43, 44, 45, 46, 47, 33,
      2,  0,  3,  5,  2,  0,  11, 9,  2,  0,  3,  5,  2,  0,  23, 17,
      49, 50, 51, 52, 49, 50, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  6,  6,  11, 9,  2,  2,  2,  2,  21, 21, 23, 17,
      24, 24, 24, 24, 37, 37, 39, 40, 41, 41, 41, 41, 45, 45, 47, 33,
      2,  2,  2,  2,  6,  6,  11, 9,  2,  2,  2,  2,  21, 21, 23, 17,
      49, 49, 49, 49, 53, 53, 55, 56, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  6,  10, 11, 9,  2,  0,  2,  5,  21, 22, 23, 17,
      24, 34, 24, 36, 37, 38, 39, 40, 41, 42, 41, 44, 45, 46, 47, 33,
      2,  0,  2,  5,  6,  10, 11, 9,  2,  0,  2,  5,  21, 22, 23, 17,
      49, 50, 49, 52, 53, 54, 55, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  6,  6,  11, 9,  2,  2,  3,  5,  21, 21, 23, 17,
      24, 24, 35, 36, 37, 37, 39, 40, 41, 41, 43, 44, 45, 45, 47, 33,
      2,  2,  3,  5,  6,  6,  11, 9,  2,  2,  3,  5,  21, 21, 23, 17,
      49, 49, 51, 52, 53, 53, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  6,  10, 11, 9,  2,  0,  3,  5,  21, 22, 23, 17,
      24, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 33,
      2,  0,  3,  5,  6,  10, 11, 9,  2,  0,  3,  5,  21, 22, 23, 17,
      49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  12, 12, 12, 12, 21, 21, 23, 17,
      24, 24, 24, 24, 24, 24, 24, 65, 41, 41, 41, 41, 45, 45, 47, 33,
      2,  2,  2,  2,  2,  2,  2,  2,  12, 12, 12, 12, 21, 21, 23, 17,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  2,  0,  2,  9,  12, 18, 12, 20, 21, 22, 23, 17,
      24, 34, 24, 36, 24, 34, 24, 40, 41, 42, 41, 44, 45, 46, 47, 33,
      2,  0,  2,  5,  2,  0,  2,  9,  12, 18, 12, 20, 21, 22, 23, 17,
      49, 50, 49, 52, 49, 50, 49, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  2,  2,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      24, 24, 35, 36, 24, 24, 39, 40, 41, 41, 43, 44, 45, 45, 47, 33,
      2,  2,  3,  5,  2,  2,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      49, 49, 51, 52, 49, 49, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  2,  0,  11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      24, 34, 35, 36, 24, 34, 39, 40, 41, 42, 43, 44, 45, 46, 47, 33,
      2,  0,  3,  5,  2,  0,  11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      49, 50, 51, 52, 49, 50, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  6,  6,  11, 9,  12, 12, 12, 12, 21, 21, 23, 17,
      24, 24, 24, 24, 37, 37, 39, 40, 41, 41, 41, 41, 45, 45, 47, 33,
      2,  2,  2,  2,  6,  6,  11, 9,  12, 12, 12, 12, 21, 21, 23, 17,
      49, 49, 49, 49, 53, 53, 55, 56, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  6,  10, 11, 9,  12, 18, 12, 20, 21, 22, 23, 17,
      24, 34, 24, 36, 37, 38, 39, 40, 41, 42, 41, 44, 45, 46, 47, 33,
      2,  0,  2,  5,  6,  10, 11, 9,  12, 18, 12, 20, 21, 22, 23, 17,
      49, 50, 49, 52, 53, 54, 55, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  6,  6,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      24, 24, 35, 36, 37, 37, 39, 40, 41, 41, 43, 44, 45, 45, 47, 33,
      2,  2,  3,  5,  6,  6,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      49, 49, 51, 52, 53, 53, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  6,  10, 11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      2,  0,  3,  5,  6,  10, 11, 9,  41, 42, 43, 44, 45, 46, 47, 33,
      4,  7,  8,  13, 14, 15, 16, 25, 26, 27, 28, 29, 30, 31, 32, 48,
      49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      24, 24, 24, 24, 24, 24, 24, 65, 41, 41, 41, 41, 45, 45, 47, 33,
      4,  4,  4,  4,  4,  4,  4,  67, 4,  4,  4,  4,  4,  4,  70, 68,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  2,  0,  2,  9,  2,  0,  2,  5,  2,  0,  2,  17,
      24, 34, 24, 36, 24, 34, 24, 40, 41, 42, 41, 44, 45, 46, 47, 33,
      4,  7,  4,  13, 4,  7,  4,  25, 4,  7,  4,  13, 4,  7,  70, 48,
      49, 50, 49, 52, 49, 50, 49, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  2,  2,  11, 9,  2,  2,  3,  5,  2,  2,  23, 17,
      24, 24, 35, 36, 24, 24, 39, 40, 41, 41, 43, 44, 45, 45, 47, 33,
      4,  4,  8,  13, 4,  4,  16, 25, 4,  4,  8,  13, 4,  4,  32, 48,
      49, 49, 51, 52, 49, 49, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  2,  0,  11, 9,  2,  0,  3,  5,  2,  0,  23, 17,
      24, 34, 35, 36, 24, 34, 39, 40, 41, 42, 43, 44, 45, 46, 47, 33,
      4,  7,  8,  13, 4,  7,  16, 25, 4,  7,  8,  13, 4,  7,  32, 48,
      49, 50, 51, 52, 49, 50, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  6,  6,  11, 9,  2,  2,  2,  2,  21, 21, 23, 17,
      24, 24, 24, 24, 37, 37, 39, 40, 41, 41, 41, 41, 45, 45, 47, 33,
      4,  4,  4,  4,  14, 14, 16, 25, 4,  4,  4,  4,  30, 30, 32, 48,
      49, 49, 49, 49, 53, 53, 55, 56, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  6,  10, 11, 9,  2,  0,  2,  5,  21, 22, 23, 17,
      24, 34, 24, 36, 37, 38, 39, 40, 41, 42, 41, 44, 45, 46, 47, 33,
      4,  7,  4,  13, 14, 15, 16, 25, 4,  7,  4,  13, 30, 31, 32, 48,
      49, 50, 49, 52, 53, 54, 55, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  6,  6,  11, 9,  2,  2,  3,  5,  21, 21, 23, 17,
      24, 24, 35, 36, 37, 37, 39, 40, 41, 41, 43, 44, 45, 45, 47, 33,
      4,  4,  8,  13, 14, 14, 16, 25, 4,  4,  8,  13, 30, 30, 32, 48,
      49, 49, 51, 52, 53, 53, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  6,  10, 11, 9,  2,  0,  3,  5,  21, 22, 23, 17,
      24, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 33,
      4,  7,  8,  13, 14, 15, 16, 25, 4,  7,  8,  13, 30, 31, 32, 48,
      49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  12, 12, 12, 12, 21, 21, 23, 17,
      24, 24, 24, 24, 24, 24, 24, 65, 41, 41, 41, 41, 45, 45, 47, 33,
      4,  4,  4,  4,  4,  4,  4,  67, 26, 26, 26, 26, 30, 30, 32, 48,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  2,  0,  2,  9,  12, 18, 12, 20, 21, 22, 23, 17,
      24, 34, 24, 36, 24, 34, 24, 40, 41, 42, 41, 44, 45, 46, 47, 33,
      4,  7,  4,  13, 4,  7,  4,  25, 26, 27, 26, 29, 30, 31, 32, 48,
      49, 50, 49, 52, 49, 50, 49, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  2,  2,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      24, 24, 35, 36, 24, 24, 39, 40, 41, 41, 43, 44, 45, 45, 47, 33,
      4,  4,  8,  13, 4,  4,  16, 25, 26, 26, 28, 29, 30, 30, 32, 48,
      49, 49, 51, 52, 49, 49, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  0,  3,  5,  2,  0,  11, 9,  12, 18, 19, 20, 21, 22, 23, 17,
      24, 34, 35, 36, 24, 34, 39, 40, 41, 42, 43, 44, 45, 46, 47, 33,
      4,  7,  8,  13, 4,  7,  16, 25, 26, 27, 28, 29, 30, 31, 32, 48,
      49, 50, 51, 52, 49, 50, 55, 56, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  6,  6,  11, 9,  12, 12, 12, 12, 21, 21, 23, 17,
      24, 24, 24, 24, 37, 37, 39, 40, 41, 41, 41, 41, 45, 45, 47, 33,
      4,  4,  4,  4,  14, 14, 16, 25, 26, 26, 26, 26, 30, 30, 32, 48,
      49, 49, 49, 49, 53, 53, 55, 56, 57, 57, 57, 57, 61, 61, 63, 1}},
    {{2,  0,  2,  5,  6,  10, 11, 9,  12, 18, 12, 20, 21, 22, 23, 17,
      24, 34, 24, 36, 37, 38, 39, 40, 41, 42, 41, 44, 45, 46, 47, 33,
      4,  7,  4,  13, 14, 15, 16, 25, 26, 27, 26, 29, 30, 31, 32, 48,
      49, 50, 49, 52, 53, 54, 55, 56, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  3,  5,  6,  6,  11, 9,  12, 12, 19, 20, 21, 21, 23, 17,
      24, 24, 35, 36, 37, 37, 39, 40, 41, 41, 43, 44, 45, 45, 47, 33,
      4,  4,  8,  13, 14, 14, 16, 25, 26, 26, 28, 29, 30, 30, 32, 48,
      49, 49, 51, 52, 53, 53, 55, 56, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      24, 24, 24, 24, 24, 65, 24, 65, 41, 41, 41, 41, 45, 46, 47, 33,
      4,  4,  4,  4,  4,  67, 4,  67, 4,  4,  4,  4,  4,  71, 70, 68,
      49, 49, 49, 49, 49, 64, 49, 64, 57, 57, 57, 57, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      24, 24, 24, 24, 24, 65, 24, 65, 41, 41, 41, 41, 45, 46, 47, 33,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      49, 49, 49, 49, 49, 64, 49, 64, 57, 57, 57, 57, 61, 62, 63, 1}},
    {{2, 0,  2, 5,  2, 0, 2, 9,  2, 0,  2, 5,  2, 0,  2, 17, 2, 0,  2, 5, 2, 66,
      2, 40, 2, 0,  2, 5, 2, 66, 2, 33, 2, 0,  2, 5,  2, 0,  2, 9,  2, 0, 2, 5,
      2, 0,  2, 17, 2, 0, 2, 5,  2, 78, 2, 56, 2, 75, 2, 76, 2, 73, 2, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      4,  4,  4,  4,  4,  67, 4,  67, 4,  4,  4,  4,  4,  71, 70, 68,
      49, 49, 49, 49, 49, 64, 49, 64, 57, 57, 57, 57, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      4,  4,  4,  4,  4,  67, 4,  67, 4,  69, 70, 72, 4,  71, 70, 68,
      49, 49, 49, 49, 49, 64, 49, 64, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      4,  4,  4,  4,  4,  4,  4,  67, 4,  69, 4,  72, 4,  71, 70, 68,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      4,  4,  4,  4,  4,  4,  4,  67, 4,  4,  70, 72, 4,  4,  70, 68,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 57, 59, 60, 61, 61, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      4,  4,  4,  4,  4,  67, 4,  67, 4,  69, 4,  72, 4,  71, 70, 68,
      49, 49, 49, 49, 49, 64, 49, 64, 57, 58, 57, 60, 61, 62, 63, 1}},
    {{2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
      4,  4,  4,  4,  4,  4,  4,  67, 4,  69, 70, 72, 4,  71, 70, 68,
      49, 49, 49, 49, 49, 49, 49, 64, 57, 58, 59, 60, 61, 62, 63, 1}},
    {{2, 0, 2, 5, 2, 0,  2, 9,  2, 0,  2, 5,  2, 0,  2, 17,
      2, 0, 2, 5, 2, 66, 2, 40, 2, 0,  2, 5,  2, 66, 2, 33,
      2, 0, 2, 5, 2, 74, 2, 25, 2, 75, 2, 76, 2, 79, 2, 48,
      2, 0, 2, 5, 2, 78, 2, 56, 2, 75, 2, 76, 2, 73, 2, 1}},
    {{2, 0,  2, 5,  2, 0, 2, 9,  2, 0,  2, 5,  2, 0,  2, 17, 2, 0,  2, 5, 2, 0,
      2, 9,  2, 0,  2, 5, 2, 66, 2, 33, 2, 0,  2, 5,  2, 74, 2, 25, 2, 0, 2, 5,
      2, 79, 2, 48, 2, 0, 2, 5,  2, 78, 2, 56, 2, 75, 2, 76, 2, 73, 2, 1}},
    {{2, 0,  2, 5,  2, 0, 2, 9,  2, 0,  2, 5, 2, 0,  2, 17, 2, 0,  2, 5,  2, 0,
      2, 9,  2, 0,  2, 5, 2, 66, 2, 33, 2, 0, 2, 5,  2, 0,  2, 9,  2, 75, 2, 76,
      2, 79, 2, 48, 2, 0, 2, 5,  2, 0,  2, 9, 2, 75, 2, 76, 2, 73, 2, 1}},
    {{2, 0, 3, 5, 2, 0, 11, 9, 2, 0,  3,  5,  2, 0,  23, 17,
      2, 0, 3, 5, 2, 0, 11, 9, 2, 0,  3,  5,  2, 66, 47, 33,
      2, 0, 3, 5, 2, 0, 11, 9, 2, 75, 77, 76, 2, 79, 32, 48,
      2, 0, 3, 5, 2, 0, 11, 9, 2, 75, 77, 76, 2, 73, 63, 1}},
    {{2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 3,  5,  2, 2, 23, 17,
      2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 3,  5,  2, 2, 47, 33,
      2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 77, 76, 2, 2, 32, 48,
      2, 2, 3, 5, 2, 2, 11, 9, 2, 2, 77, 76, 2, 2, 63, 1}},
    {{2, 0,  2, 5,  2, 0, 2, 9,  2, 0,  2, 5,  2, 0,  2, 17, 2, 0,  2, 5, 2, 66,
      2, 40, 2, 0,  2, 5, 2, 66, 2, 33, 2, 0,  2, 5,  2, 74, 2, 25, 2, 0, 2, 5,
      2, 79, 2, 48, 2, 0, 2, 5,  2, 78, 2, 56, 2, 75, 2, 76, 2, 73, 2, 1}},
    {{2, 0, 2, 5, 2, 0,  2, 9,  2, 0,  2, 5,  2, 0,  2, 17,
      2, 0, 2, 5, 2, 0,  2, 9,  2, 0,  2, 5,  2, 66, 2, 33,
      2, 0, 2, 5, 2, 74, 2, 25, 2, 75, 2, 76, 2, 79, 2, 48,
      2, 0, 2, 5, 2, 78, 2, 56, 2, 75, 2, 76, 2, 73, 2, 1}},
}};

static const int __learned_dfa_register_6 = [] {
    learned_dfa::dfas().register_dfa(INITIAL_STATE, ACCEPTING, TRANS, "6");
    return 0;
}();
} // namespace learned_dfa_6

#include <atcoder/modint>
using mint = atcoder::modint1000000007;
using sparse_matrix_type = std::vector<std::vector<std::pair<int, mint>>>;

std::vector<mint> matrix_vector_product(sparse_matrix_type &A,
                                        std::vector<mint> &b) {
    int n = int(b.size());
    assert(A.size() == n);

    std::vector<mint> res(n);
    for (int i = 0; i < n; i += 1) {
        for (auto [j, val] : A[i]) {
            assert(j >= 0 && j < n);
            res[i] += val * b[j];
        }
    }
    return res;
}

int main(void) {
    std::string h;
    int w;
    std::cin >> h >> w;

    auto dfa = learned_dfa::dfas().get(h);
    auto A = dfa.sparse_transition_count_matrix<mint>();
    int n = dfa.state_size();
    std::vector<mint> b(n);
    for (int i = 0; i < n; i += 1) {
        b[i] = dfa.is_accepting(i);
    }

    for (int i = 0; i < w; i += 1) {
        b = matrix_vector_product(A, b);
    }
    std::cout << b[dfa.index_of_initial_state()].val() << "\n";
    return 0;
}
