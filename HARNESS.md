# Как пользоваться этим каркасом (удалить из репозитория после подачи не обязательно — он раскрыт в DISCLOSURE)

0. Накануне на каждом ноутбуке: `.\scripts\preflight.ps1 -Wheels`. Роли — `docs/TEAM.md`.
1. После получения репозитория от платформы: `git clone <repo>` и запуск `bootstrap` (см. ниже), выбрать номер трека.
2. Вставить кейс организаторов дословно в `docs/CASE.md`.
3. Claude Code: `/kickoff <трек>`. Codex: `codex "Выполни prompts/00-kickoff.md"`. Другие агенты: «Прочитай AGENTS.md и выполни prompts/00-kickoff.md».
4. Каждый час: `/hour N` или `scripts/checkpoint.* N "<результат>"`.
5. С 3-го часа: `/judge`. В конце: `/submit <URL>`.

Bootstrap (из папки с каркасом, PowerShell):
    .\scripts\bootstrap.ps1 -Target C:\path\to\platform-repo -Track 5
Git Bash:
    ./scripts/bootstrap.sh /c/path/to/platform-repo 5
