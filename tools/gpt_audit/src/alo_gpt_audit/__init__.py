"""alo-gpt-audit — GPT Pro 目付け役 監査レーンの close/status ツール (v0.2 spec).

中核ルール:
    to_gpt/ 直下は GPT がまだ答えていない REQUEST だけにする。
    RESULT を返したら、元 REQUEST は必ず to_gpt/processed/ へ退避する。

このパッケージは「フォルダ位置=状態」を機械的に強制する。状態の SoT は
あくまでフォルダ位置とファイル実体であり、台帳はそこから派生する控えである。
"""

__version__ = "0.2.0"
