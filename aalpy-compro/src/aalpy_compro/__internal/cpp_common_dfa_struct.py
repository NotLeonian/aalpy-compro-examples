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
        "string",
        "vector",
    ]:
        res.append(f"#include <{header_name}>")
    res.append("")
    res.append(f"namespace {namespace} {{")
    res.append("""\
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

    int state_size() const noexcept { return n; }
    int alphabet_size() const noexcept { return sigma; }
    int index_of_initial_state() const noexcept { return initial_state; }

    const std::string &get_key() const & noexcept { return key; }

    bool is_accepting(int src) const {
        if (src < 0 || src >= n) {
            return false;
        }
        return static_cast<bool>(accepting[src]);
    }

    int next(int src, int label) const {
        if (src < 0 || src >= n) {
            return -1;
        }
        if (label < 0 || label >= sigma) {
            return -1;
        }
        return trans[src][label];
    }
};

class DFAs {
  private:
    std::vector<DFA> dfas;

  public:
    const std::vector<DFA> &operator()() const & noexcept { return dfas; }

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

    const DFA &get(const std::string &key) const & {
        int i = index_of(key);
        if (i < 0) {
            std::abort();
        }
        return dfas[i];
    }

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
""")
    res.append(f"}} // namespace {namespace}")
    res.append("")

    return "\n".join(res)
