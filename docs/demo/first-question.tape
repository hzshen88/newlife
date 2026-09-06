# A VHS tape (https://github.com/charmbracelet/vhs): `vhs docs/demo/first-question.tape`
# records docs/demo/first-question.gif and .mp4. It drives the *released* package, not the
# checkout: before recording, create the environment it runs in
#
#     uv venv /tmp/newlife-demo-venv --python 3.12
#     uv pip install --python /tmp/newlife-demo-venv/bin/python newlife
#
# The world is the scaffold's placeholder model, the same as docs/first-question.md; the
# two "# ..." lines are narration for the steps an AI does from a conversation.

Output docs/demo/first-question.gif
Output docs/demo/first-question.mp4

Set Shell "bash"
Set FontSize 15
Set Width 1100
Set Height 680
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 30ms
Set Framerate 24

Hide
Type "export PATH=/tmp/newlife-demo-venv/bin:$PATH && mkdir -p /tmp/newlife-demo && cd /tmp/newlife-demo && rm -rf my-research && clear" Enter
Show

Type "newlife --version" Enter
Sleep 1.5s
Type "newlife start my-research" Enter
Sleep 4s
Type "cd my-research && Q=questions/2026-09-06-first-question" Enter
Sleep 800ms
Type "newlife init 2026-09-06-first-question" Enter
Sleep 4s
Type "clear && newlife status $Q" Enter
Sleep 5s
Type "newlife freeze $Q" Enter
Sleep 5s
Type "clear" Enter
Type "# your AI fills the six anchors of goal.md from a conversation; a demo waives the stage:" Enter
Type "echo '<!--@goal_gate: not_applicable — demo of the mechanics, not a question-->' >> $Q/goal.md" Enter
Sleep 1.5s
Type "newlife pilot $Q" Enter
Sleep 5s
Type "clear" Enter
Type "# everything the pilot showed is now seen; the criteria say so, row by row:" Enter
Type "sed -i '' 's/(your positive control) | | |/output increases across the sweep | strictly_increasing(observed) | seen |/' $Q/prereg.md" Enter
Type "echo '<!--@pilot_gate: no_blind_waived — the placeholder model has nothing worth predicting blind-->' >> $Q/prereg.md" Enter
Sleep 1.5s
Type "newlife freeze $Q" Enter
Sleep 5s
Type "clear && newlife run $Q" Enter
Sleep 3.5s
Type "git add $Q/results && git commit -qm 'verdict' -- $Q/results" Enter
Sleep 1.5s
Type "clear && newlife audit $Q" Enter
Sleep 8s
