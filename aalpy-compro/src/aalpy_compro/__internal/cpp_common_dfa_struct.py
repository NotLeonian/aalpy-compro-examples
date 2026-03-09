def common_dfa_struct(*, namespace: str = "learned_dfa") -> str:
    """
    DFA の構造体の C++ のソースコードを返す
    """

    # TODO: DFA のメソッドを実装する

    res: list[str] = []
    for header_name in [
        "algorithm",
        "array",
        "cassert",
        "cstddef",
        "cstdlib",
        "functional",
        "iterator",
        "string",
        "type_traits",
        "utility",
        "vector",
    ]:
        res.append(f"#include <{header_name}>")
    res.append("")
    res.append(f"namespace {namespace} {{")
    res.append("""\
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
                if (is_accepting(i) && ans < dp_table[i]) {
                    ans = dp_table[i];
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
}\
""")
    res.append(f"}} // namespace {namespace}")
    res.append("")

    return "\n".join(res)
