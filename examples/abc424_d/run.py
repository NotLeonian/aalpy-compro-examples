#!/usr/bin/env -S uv run
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys


@contextmanager
def render_to_temp_path(
    template_path: Path,
    context: Mapping[str, object],
    *,
    filename: str = "generated.py",
) -> Iterator[Path]:
    """
    template_path のファイルに
    context の値を代入して
    一時ファイルとして書き出す
    """

    rendered = template_path.read_text(encoding="utf-8").format_map(context)

    with TemporaryDirectory(prefix="aalpy-compro-tmpdir-") as tmpdir:
        output_path = Path(tmpdir) / filename
        output_path.write_text(rendered, encoding="utf-8", newline="\n")
        yield output_path


output_filename = "learned_dfa.cpp"
property_filename = "property.py"
template_filename = f"{property_filename}.tmpl"

script_dir = Path(__file__).resolve().parent
output_path = script_dir / output_filename
template_path = script_dir / template_filename

with open(output_path, "w", encoding="utf-8") as f:

    def common_args() -> list[str]:
        res: list[str] = []
        res += ["--kind", "common"]
        res += ["--namespace", "learned_dfa"]
        return res

    def learn_args(
        *,
        key: str,
        property_path: Path,
    ) -> list[str]:
        res: list[str] = []
        res += ["--kind", "learn"]
        res += ["--algorithm", "lstar"]
        res += ["--path", str(property_path)]
        res += ["--namespace", "learned_dfa"]
        res += ["--key", key]
        res += ["--print-level", str(0)]
        return res

    def write(args: list[str]) -> None:
        subprocess.run(
            [sys.executable, "-u", "-m", "aalpy_compro"] + args,
            cwd=script_dir,
            stdin=subprocess.DEVNULL,
            stdout=f,
            # 正常に処理が行われれば標準エラー出力が f に書き込まれることはないが
            # エラーが発生した場合は書き込まれるかもしれないことに注意
            stderr=subprocess.STDOUT,
            check=True,
        )

    write(common_args())

    MAX_W = 7
    for w in range(2, MAX_W + 1):
        key = str(w)
        context = {"W": w}

        print(f"key: {key}", file=sys.stderr)

        with render_to_temp_path(
            template_path,
            context,
            filename=property_filename,
        ) as property_path:
            write(learn_args(key=key, property_path=property_path))
