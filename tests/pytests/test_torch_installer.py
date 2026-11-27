"""Tests for modules.torch_installer — frozen-app detection, paths, GPU index URL."""

import os
import subprocess
import sys

from modules import torch_installer


# ── is_frozen / paths ─────────────────────────────────────────────────────────

def test_is_frozen_false_from_source(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert torch_installer.is_frozen() is False


def test_is_frozen_true_when_set(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert torch_installer.is_frozen() is True


def test_app_root_and_subdirs(monkeypatch, tmp_path):
    exe = tmp_path / "SnapshotPackCreator.exe"
    monkeypatch.setattr(sys, "executable", str(exe))
    assert torch_installer.app_root() == str(tmp_path)
    assert torch_installer.internal_dir() == os.path.join(str(tmp_path), "_internal")
    assert torch_installer.portable_python_exe() == os.path.join(
        str(tmp_path), "tools", "python", "python.exe"
    )


# ── is_torch_installed ────────────────────────────────────────────────────────

def test_is_torch_installed_false_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app.exe"))
    assert torch_installer.is_torch_installed() is False


def test_is_torch_installed_true_when_present(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app.exe"))
    os.makedirs(tmp_path / "_internal" / "torch")
    assert torch_installer.is_torch_installed() is True


# ── detect_torch_index_url ────────────────────────────────────────────────────

def test_detect_torch_index_url_nvidia_present(monkeypatch):
    def _fake_run(cmd, **kwargs):
        assert cmd[0] == "nvidia-smi"
        return subprocess.CompletedProcess(cmd, 0, stdout="GPU 0: NVIDIA GeForce RTX 5080", stderr="")
    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert torch_installer.detect_torch_index_url() == torch_installer.TORCH_INDEX_URLS["cu128"]


def test_detect_torch_index_url_no_nvidia(monkeypatch):
    def _fake_run(cmd, **kwargs):
        if cmd[0] == "nvidia-smi":
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not found")
        return subprocess.CompletedProcess(cmd, 0, stdout="Intel(R) UHD Graphics", stderr="")
    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert torch_installer.detect_torch_index_url() == torch_installer.TORCH_INDEX_URLS["cpu"]


def test_detect_torch_index_url_falls_back_to_cpu_on_errors(monkeypatch):
    def _fake_run(cmd, **kwargs):
        raise OSError("command not found")
    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert torch_installer.detect_torch_index_url() == torch_installer.TORCH_INDEX_URLS["cpu"]
