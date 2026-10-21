# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

from __future__ import annotations


def test_tui_banner_displays_codeharbor_beacon_identity() -> None:
    from codeharbor.app import CodeHarborApp

    banner = CodeHarborApp._make_banner(
        model="deepseek-chat",
        work_dir="D:/workspace",
    ).plain

    assert "CodeHarbor v0.2.0" in banner
    assert "◢█◣" in banner
    assert "deepseek-chat" in banner
    assert "D:/workspace" in banner
    assert "MewCode" not in banner
