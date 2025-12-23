from denario.llm import models


def main() -> None:
    required = [
        "gemini-3-flash",
        "gemini-3-pro",
        "gpt-5.2",
        "gpt-5.2-pro",
        "claude-4.5-sonnet",
        "claude-4.5-opus",
        "claude-4.5-haiku",
    ]

    missing = [name for name in required if name not in models]
    if missing:
        raise SystemExit(f"Missing model aliases: {missing}")

    print("Model alias smoke test passed:")
    for name in required:
        print(f"- {name} -> {models[name].name}")


if __name__ == "__main__":
    main()
