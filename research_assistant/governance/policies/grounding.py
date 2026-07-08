async def apply(run: dict, _context: dict) -> dict:
    if run["sources"] and not run["tools"] and run["error"] is None:
        return {
            **run,
            "error": "ungrounded_answer_blocked",
            "answer": (
                "The assistant produced an answer without consulting the "
                "platform's tools, so it has been withheld. Please try again."
            ),
            "sources": [],
        }
    return run
