# Instructions for AI agents

- **Delivery.** Never push to `main`. Push a branch named `claude/<topic>`; the
  owner opens and merges the pull request and makes the tags. Commit as
  `Claude <claude@anthropic.invalid>`.
- **Plan.** [`PLAN.md`](PLAN.md) holds the decisions and the order of work.
  Update it when a step is done or a decision changes.
- **Behaviour changes are checked.** Before a tag, render one real deck with
  `--tts silent` with the previous tag and the new one, and say in the commit
  what differs (page SHA-256, clips) and why.
- **Users pin tags.** wpmw, oziewicz and the `pptx-voiceover` skill install a
  tag, so a change reaches them only when they move to a new tag. Say in
  `CHANGELOG.md` what a project must change when it does.
