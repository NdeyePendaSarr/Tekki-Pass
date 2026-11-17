// Commit messages must follow Conventional Commits: https://www.conventionalcommits.org
// Example: "feat(api): add attestation request endpoint"
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // Keep the scope list short and aligned with the monorepo layout.
    "scope-enum": [2, "always", ["api", "web", "docs", "adr", "ci", "docker", "deploy", "deps", "github"]],
  },
};
