#!/usr/bin/env -S uv run
import subprocess
import sys
from pathlib import Path

output_filename = "learned_dfa.cpp"
property_filename = "property.py"

script_dir = Path(__file__).resolve().parent
output_path = script_dir / output_filename
property_path = script_dir / property_filename

with open(output_path, "w", encoding="utf-8") as f:

    def common_args() -> list[str]:
        res: list[str] = []
        res += ["--kind", "common"]
        res += ["--namespace", "learned_dfa"]
        return res

    def regex_args(
        *,
        key: str,
        property_path: Path,
    ) -> list[str]:
        res: list[str] = []
        res += ["--kind", "regex"]
        res += ["--path", str(property_path)]
        res += ["--namespace", "learned_dfa"]
        res += ["--key", key]
        return res

    def write(args: list[str]) -> None:
        subprocess.run(
            [sys.executable, "-u", "-m", "aalpy_compro"] + args,
            cwd=script_dir,
            stdin=subprocess.DEVNULL,
            stdout=f,
            # 警告やエラーは、生成するソースコードに混ぜず、親プロセスの標準エラー出力に流す。
            stderr=None,
            check=True,
        )

    write(common_args())

    key = "result"
    write(regex_args(key=key, property_path=property_path))
