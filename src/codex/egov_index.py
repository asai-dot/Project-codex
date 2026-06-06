"""e-gov 法令定義 jsonl から法令名/条文の索引を構築する.

入力: data/egov/egov_statutory_definitions_ALL.jsonl (1 行 1 定義)
      フィールド: term, definition, law_id, law_name, article, item, uri, ...

提供する索引:
  - name_to_law   : 法令名 -> law_id (ユニークな対応のみ)
  - known_articles: (law_id, article) -> uri   (定義が存在する条のみ)
  - law_names     : 長い順にソートした法令名リスト (貪欲マッチ用)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

DEFAULT_EGOV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "egov",
    "egov_statutory_definitions_ALL.jsonl",
)


def egov_article_uri(law_id: str, article: str) -> str:
    """egov の正準 URI を生成 (item なし条レベル)。"""
    return f"egov:{law_id}:art:{article}"


@dataclass
class EgovIndex:
    name_to_law: dict[str, str] = field(default_factory=dict)
    law_name_by_id: dict[str, str] = field(default_factory=dict)
    known_articles: dict[tuple[str, str], str] = field(default_factory=dict)
    law_names: list[str] = field(default_factory=list)
    # 同名で複数 law_id に割れる曖昧な法令名 (リンク時は曖昧フラグを立てる)
    ambiguous_names: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, path: str = DEFAULT_EGOV_PATH) -> "EgovIndex":
        path = os.path.abspath(path)
        name_to_ids: dict[str, set[str]] = {}
        law_name_by_id: dict[str, str] = {}
        known_articles: dict[tuple[str, str], str] = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                o = json.loads(line)
                lid = o.get("law_id")
                lname = o.get("law_name")
                art = o.get("article")
                if not lid or not lname:
                    continue
                name_to_ids.setdefault(lname, set()).add(lid)
                law_name_by_id[lid] = lname
                if art not in (None, ""):
                    art = str(art)
                    known_articles[(lid, art)] = o.get("uri") or egov_article_uri(lid, art)

        name_to_law: dict[str, str] = {}
        ambiguous: set[str] = set()
        for name, ids in name_to_ids.items():
            if len(ids) == 1:
                name_to_law[name] = next(iter(ids))
            else:
                ambiguous.add(name)
                # 曖昧でも代表 (辞書順最小 law_id) を入れておく
                name_to_law[name] = sorted(ids)[0]

        # 貪欲マッチのため長い順
        law_names = sorted(name_to_law.keys(), key=len, reverse=True)
        return cls(
            name_to_law=name_to_law,
            law_name_by_id=law_name_by_id,
            known_articles=known_articles,
            law_names=law_names,
            ambiguous_names=ambiguous,
        )

    def has_definition(self, law_id: str, article: str) -> bool:
        return (law_id, str(article)) in self.known_articles
