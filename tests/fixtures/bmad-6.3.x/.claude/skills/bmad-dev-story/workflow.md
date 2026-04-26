# Dev Story Workflow

<!-- INTENTIONALLY LEGACY (BMAD 6.3.x fixture). Do NOT migrate the `/pulse-track-*`
     references below to `/bmad-pulse-track-*`. This file simulates a pre-v0.4.0
     consumer project where PULSE auto-injected workflow steps with the old
     slash commands. The cleanup-legacy.py regression test asserts these strings
     are removed; "fixing" the names here would falsify that test. -->

<workflow>
  <step n="1" goal="Find next ready story">
    <action>Read sprint-status.yaml</action>
  </step>

  <step n="4" goal="Mark story in-progress">
    <action>Update status to in-progress</action>
  </step>

  <!-- PULSE:auto-inject:start -->
  <step n="4.5" goal="PULSE — Track Start">
    <action>Run /pulse-track-start {{story_key}}</action>
  </step>
  <!-- PULSE:auto-inject:end -->

  <step n="5" goal="Implement">
    <action>Write code</action>
  </step>

  <!-- PULSE:auto-inject:start -->
  <step n="10.5" goal="PULSE — Track Done">
    <action>Run /pulse-track-done {{story_key}}</action>
  </step>
  <!-- PULSE:auto-inject:end -->
</workflow>
