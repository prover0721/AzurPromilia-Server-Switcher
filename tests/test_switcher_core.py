# -*- coding: utf-8 -*-
"""Unit tests for AzurPromilia-Server-Switcher core modules."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.anti_blur import apply_anti_blur_patch, has_anti_blur_backup, restore_anti_blur_backup
from core.game_locator import detect_server_from_files, inspect_installation, resolve_game_root
from core.resource_pool import (
    audit_resource_links,
    extract_channel_source,
    link_shared_resources,
    switch_cn_channel,
    unlink_to_independent,
)


def _create_fake_game_root(base: Path, is_bilibili: bool = False) -> Path:
    game_root = base / "AzurPromilia_Game"
    (game_root / "mj_sdk" / "res").mkdir(parents=True, exist_ok=True)
    (game_root / "AzurPromilia.exe").write_bytes(b"EXE")
    (game_root / "mj_sdk" / "res" / "app_config.dat").write_bytes(b"BILI" if is_bilibili else b"OFFI")

    sdk_dir = game_root / "AzurPromilia_Data" / "Plugins" / "mj_sdk"
    sdk_dir.mkdir(parents=True, exist_ok=True)
    (sdk_dir / "PCGameSDK.dll").write_bytes(b"SDK")
    if is_bilibili:
        (sdk_dir / "BLPlatform64").mkdir(exist_ok=True)
        (sdk_dir / "BLPlatform64" / "bili.dll").write_bytes(b"BILI_DLL")

    pkg = game_root / "AzurPromilia_Data" / "StreamingAssets" / ".res" / "default_package"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "bundle_01.ab").write_bytes(b"A" * 4096)
    return game_root


class TestSwitcherCore(unittest.TestCase):
    def test_resolve_and_detect_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bili_root = _create_fake_game_root(root / "bili", is_bilibili=True)
            offi_root = _create_fake_game_root(root / "AzurPromilia bilibili", is_bilibili=False)

            self.assertEqual(resolve_game_root(root / "bili"), bili_root)
            self.assertEqual(detect_server_from_files(bili_root), "bilibili")
            # Folder named bilibili without BLPlatform64 must still detect as official
            self.assertEqual(detect_server_from_files(offi_root, offi_root.parent), "official")
            # Hybrid state (official app_config.dat + BLPlatform64) must not falsely claim bilibili
            (offi_root / "AzurPromilia_Data" / "Plugins" / "mj_sdk" / "BLPlatform64").mkdir(exist_ok=True)
            (offi_root / "mj_sdk" / "res" / "app_config.dat").write_bytes(
                (Path(__file__).resolve().parent.parent / "assets" / "cn_sources" / "official" / "app_config.dat").read_bytes()
            )
            self.assertEqual(detect_server_from_files(offi_root, offi_root.parent), "official")

            inst = inspect_installation(root / "bili", measure_size=True)
            self.assertIsNotNone(inst)
            self.assertEqual(inst.detected_server, "bilibili")
            self.assertTrue(inst.has_bl_platform)

    @patch("core.resource_pool.is_game_running", return_value=False)
    def test_cn_channel_extract_and_switch(self, _mock_running):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = root / "sources"
            backups = root / "backups"
            bili_root = _create_fake_game_root(root / "cn_client", is_bilibili=True)
            offi_root = _create_fake_game_root(root / "offi_donor", is_bilibili=False)

            extract_channel_source(bili_root, "bilibili", sources_dir=sources)
            extract_channel_source(offi_root, "official", sources_dir=sources)

            switch_cn_channel(bili_root, "bilibili", "official", sources_dir=sources, backups_dir=backups)
            self.assertEqual(detect_server_from_files(bili_root), "official")
            self.assertEqual((bili_root / "mj_sdk" / "res" / "app_config.dat").read_bytes(), b"OFFI")

            switch_cn_channel(bili_root, "official", "bilibili", sources_dir=sources, backups_dir=backups)
            self.assertEqual(detect_server_from_files(bili_root), "bilibili")
            self.assertEqual((bili_root / "mj_sdk" / "res" / "app_config.dat").read_bytes(), b"BILI")

    @patch("core.resource_pool.is_game_running", return_value=False)
    def test_hardlink_pool_and_unlink(self, _mock_running):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_game = _create_fake_game_root(root / "cn", is_bilibili=True)
            jp_game = root / "jp" / "AzurPromilia_Game"
            (jp_game / "AzurPromilia_Data" / "StreamingAssets" / ".res").mkdir(parents=True, exist_ok=True)
            (jp_game / "AzurPromilia.exe").write_bytes(b"JP_EXE")

            linked, skipped = link_shared_resources(src_game, jp_game)
            self.assertEqual(linked, 1)
            self.assertEqual(skipped, 0)

            audit = audit_resource_links([src_game, jp_game])
            self.assertEqual(audit.total_files, 2)
            self.assertEqual(audit.linked_files, 2)
            self.assertEqual(audit.saved_bytes, 4096)

            broken = unlink_to_independent(jp_game)
            self.assertEqual(broken, 1)
            audit_after = audit_resource_links([src_game, jp_game])
            self.assertEqual(audit_after.linked_files, 0)
            self.assertEqual(audit_after.saved_bytes, 0)

    @patch("core.anti_blur.is_game_running", return_value=False)
    def test_anti_blur_apply_and_restore(self, _mock_running):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game_root = _create_fake_game_root(root / "game", is_bilibili=True)
            patch_dir = root / "patch"
            patch_bundle = patch_dir / "AzurPromilia_Data" / "StreamingAssets" / ".res" / "default_package"
            patch_bundle.mkdir(parents=True, exist_ok=True)
            (patch_bundle / "bundle_01.ab").write_bytes(b"PATCHED")
            backups = root / "backups"

            replaced, backed_up = apply_anti_blur_patch(game_root, patch_dir, backups_dir=backups)
            self.assertEqual(replaced, 1)
            self.assertEqual(backed_up, 1)
            self.assertTrue(has_anti_blur_backup(backups))
            target_file = game_root / "AzurPromilia_Data" / "StreamingAssets" / ".res" / "default_package" / "bundle_01.ab"
            self.assertEqual(target_file.read_bytes(), b"PATCHED")

            restored = restore_anti_blur_backup(game_root, backups_dir=backups)
            self.assertEqual(restored, 1)
            self.assertEqual(target_file.read_bytes(), b"A" * 4096)


if __name__ == "__main__":
    unittest.main()
