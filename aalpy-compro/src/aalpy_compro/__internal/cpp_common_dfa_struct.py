def common_dfa_struct(*, namespace: str = "learned_dfa") -> str:
    """
    DFA の構造体の C++ のソースコードを返す
    """

    # TODO: DFA のメソッドを実装する

    res: list[str] = []
    for header_name in ["algorithm", "array", "cstddef", "cstdlib", "string", "vector"]:
        res.append(f"#include <{header_name}>")
    res.append("")
    res.append(f"namespace {namespace} {{")
    res.append("struct DFA {")
    res.append("    int n;")
    res.append("    int sigma;")
    res.append("    int initial_state;")
    res.append("")
    res.append("    std::vector<unsigned char> accepting;")
    res.append("    std::vector<std::vector<int>> trans;")
    res.append("")
    res.append("    std::string key;")
    res.append("")
    res.append("    DFA(const int n, const int sigma, const int initial_state,")
    res.append("        const std::vector<unsigned char> &accepting,")
    res.append(
        "        const std::vector<std::vector<int>> &trans, const std::string &key)"
    )
    res.append("        : n(n), sigma(sigma), initial_state(initial_state),")
    res.append("          accepting(accepting), trans(trans), key(key) {}")
    res.append("")
    res.append("    template <std::size_t N, std::size_t SIGMA>")
    res.append(
        "    DFA(const int initial_state, const std::array<unsigned char, N> &acc,"
    )
    res.append(
        "        const std::array<std::array<int, SIGMA>, N> &tr, const std::string &key)"
    )
    res.append("        : n(N), sigma(SIGMA), initial_state(initial_state),")
    res.append(
        "          accepting(acc.begin(), acc.end()), trans(N, std::vector<int>(SIGMA)),"
    )
    res.append("          key(key) {")
    res.append("        for (int i = 0; i < N; i += 1) {")
    res.append("            for (int j = 0; j < SIGMA; j += 1) {")
    res.append("                trans[i][j] = tr[i][j];")
    res.append("            }")
    res.append("        }")
    res.append("    }")
    res.append("};")
    res.append("")
    res.append("struct DFAs {")
    res.append("    std::vector<DFA> dfas;")
    res.append("")
    res.append("    const int index_of(const std::string &key) const {")
    res.append("        auto it = std::find_if(")
    res.append("            dfas.begin(), dfas.end(),")
    res.append(
        "            [&key](const DFA &dfa) -> bool { return dfa.key == key; });"
    )
    res.append("        if (it != dfas.end()) {")
    res.append("            return static_cast<int>(it - dfas.begin());")
    res.append("        } else {")
    res.append("            return -1;")
    res.append("        }")
    res.append("    }")
    res.append("")
    res.append("    const DFA &get(const std::string &key) const {")
    res.append("        int i = index_of(key);")
    res.append("        if (i < 0) {")
    res.append("            std::abort();")
    res.append("        }")
    res.append("        return dfas[i];")
    res.append("    }")
    res.append("")
    res.append("    template <std::size_t N, std::size_t SIGMA>")
    res.append("    void register_dfa(const int initial_state,")
    res.append("                      const std::array<unsigned char, N> &acc,")
    res.append("                      const std::array<std::array<int, SIGMA>, N> &tr,")
    res.append("                      const std::string &key) {")
    res.append("        DFA dfa(initial_state, acc, tr, key);")
    res.append("")
    res.append("        int i = index_of(key);")
    res.append("        if (i >= 0) {")
    res.append("            std::abort(); // already exists")
    res.append("        }")
    res.append("        dfas.emplace_back(dfa);")
    res.append("    }")
    res.append("};")
    res.append("")
    res.append("inline DFAs &dfas() {")
    res.append("    static DFAs dfas;")
    res.append("    return dfas;")
    res.append("}")
    res.append(f"}} // namespace {namespace}")
    res.append("")

    return "\n".join(res)
