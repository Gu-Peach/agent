from ddgs import DDGS


def search(query: str) -> str:
    """
    一个基于 DDGS 的网页搜索工具。
    它不需要额外 API Key，适合本地 ReAct demo 使用。
    """
    print(f"🔍 正在执行 [DDGS] 网页搜索: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="cn-zh", max_results=3))

        if results:
            snippets = []
            for i, result in enumerate(results, start=1):
                title = result.get("title", "")
                body = result.get("body", "")
                href = result.get("href", "")
                snippets.append(f"[{i}] {title}\n{body}\n来源: {href}")
            return "\n\n".join(snippets)
        
        return f"对不起，没有找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"
