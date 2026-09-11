"""Invariant tests for skills/bmad-pulse-setup/assets/module.yaml.

Path resolution invariants — guard against double-interpolation regressions
where a `result` template prefixes a token (e.g. `{project-root}/`) onto a
`{value}` that already starts with another resolved token (e.g. `{output_folder}`,
which itself begins with `{project-root}`). That class of bug surfaces only
when the BMAD installer writes the resolved value into `_bmad/config.yaml`
and skills then expand it twice at runtime.

Reference: https://github.com/nidelson/bmad-module-pulse/issues/15
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
MODULE_YAML = REPO_ROOT / "skills/bmad-pulse-setup/assets/module.yaml"
MODULE_YAML_ROOT_SYMLINK = REPO_ROOT / "module.yaml"


def _load_module_yaml() -> dict:
    return yaml.safe_load(MODULE_YAML.read_text())


def test_root_symlink_resolves_to_canonical_manifest():
    """v0.4.5 exposes module.yaml at the repo root as a symlink for
    discoverability (third-party validators, marketplace scrapers,
    casual readers). The canonical file stays inside the setup skill
    so the BMAD installer can copy it to the consumer project at
    install time. This test pins the link so it does not drift."""
    assert MODULE_YAML_ROOT_SYMLINK.exists(), (
        "module.yaml at repo root is missing — must exist as a symlink "
        "to skills/bmad-pulse-setup/assets/module.yaml for discoverability."
    )
    assert MODULE_YAML_ROOT_SYMLINK.is_symlink(), (
        "module.yaml at repo root must be a symlink (not a duplicate file) "
        "to avoid drift with the canonical manifest."
    )
    resolved = MODULE_YAML_ROOT_SYMLINK.resolve()
    assert resolved == MODULE_YAML.resolve(), (
        f"module.yaml symlink at repo root resolves to {resolved}, "
        f"expected {MODULE_YAML.resolve()}"
    )


def test_path_results_do_not_double_prefix_project_root():
    """`result` for path-typed entries must not prefix `{project-root}/` when
    the corresponding `default` already begins with `{output_folder}`.

    `{output_folder}` resolves to `{project-root}/_bmad-output` per BMAD core,
    so prefixing again produces `{project-root}/{project-root}/...` —
    invalid path at runtime.
    """
    data = _load_module_yaml()
    path_keys = ("pulse_data_folder", "pulse_dashboard_folder")

    for key in path_keys:
        entry = data.get(key)
        assert entry is not None, f"missing {key} in module.yaml"
        default = entry.get("default", "")
        result = entry.get("result", "")

        if default.startswith("{output_folder}"):
            assert "{project-root}" not in result, (
                f"{key}: result template '{result}' double-prefixes "
                f"{{project-root}} on top of default '{default}' which "
                f"already starts with {{output_folder}}"
            )


def test_path_results_use_value_token():
    """Path entries must propagate `{value}` so user customizations stick."""
    data = _load_module_yaml()
    for key in ("pulse_data_folder", "pulse_dashboard_folder"):
        entry = data[key]
        assert "{value}" in entry["result"], (
            f"{key}: result template must contain {{value}} to honor user input"
        )


# ── post_install_message: the only signal a stale loop plugin ever gets ──────
#
# The loop plugin is a COPY, made by bmad-pulse-setup:
#
#     cp ./assets/loop-plugin/* "{project-root}/.bmad-loop/plugins/pulse/"
#
# A BMAD module update refreshes `skills/` and never touches that copy, so it
# stays frozen at whatever shipped on install day. #123 proved the cost: the
# closing hook moved from `post_story` to `post_commit` (the former cannot run
# at all — bmad-loop#779), and every existing install kept the broken seam. The
# hook is non-blocking by design, so the failure is silent: the run reports
# "1 done" and the story's metrics are simply never written.
#
# The BMAD installer reads `post_install_message` from the module manifest and
# renders a blocking "⚑ Action needed" panel that the user must acknowledge
# (`installer.js` `_displayPostInstallMessages`, reached from `install()` —
# which is also the update path). That panel is the only place this can be said.


def test_manifest_carries_a_post_install_message():
    """Without this field the installer shows nothing (`if (!message) continue`),
    and a user updating BMAD has no way to learn the loop plugin went stale."""
    data = _load_module_yaml()
    assert data.get("post_install_message"), (
        "module.yaml must declare post_install_message — it is the installer's "
        "only 'Action needed' channel, and it fires on update as well as install"
    )


def test_post_install_message_names_the_command_that_fixes_it():
    """A notice that does not say what to run is a notice that gets dismissed.
    The setup skill is already the supported re-run/migration path (#73)."""
    msg = _load_module_yaml().get("post_install_message", "")
    assert "/bmad-pulse-setup" in msg


def test_post_install_message_states_the_consequence_of_ignoring_it():
    """The whole problem is that the failure is invisible. If the panel does not
    say the stale files fail without complaining, the reader has no reason to
    act on a message that otherwise reads like routine post-install noise."""
    msg = _load_module_yaml().get("post_install_message", "").lower()
    assert any(w in msg for w in ("quietly", "silent", "silently", "without warning"))


def test_post_install_message_is_not_conditional_on_another_tool():
    """The message is about PULSE. An earlier draft opened with "If this project
    is driven by bmad-loop" and led with plugin paths — which makes the reader
    decide whether they are in scope before they know what the message is about,
    and gets skipped by exactly the people who needed it. The action is the same
    for everyone and harmless to repeat, so it is stated unconditionally.

    Naming internals here also dates the text the next time setup writes
    somewhere new: the reason to re-run is 'setup put files in your project',
    not any one file's path."""
    msg = _load_module_yaml().get("post_install_message", "").lower()
    for leak in ("bmad-loop", ".bmad-loop", "plugin"):
        assert leak not in msg, (
            f"{leak!r} makes the panel look like it applies to someone else — "
            "keep the message about PULSE and the action the user must take"
        )
    assert not msg.lstrip().startswith("if "), (
        "do not open with a condition the reader has to evaluate before they "
        "know what the message is for"
    )
