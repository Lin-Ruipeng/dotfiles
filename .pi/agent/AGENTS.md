# 用户级指令

问用户任何问题都调 `ask_user_question`，让问题变成可点选的 panel —— skill / prompt template 写着
`❓ Q1` / `➡️ 推荐答案` 这类文本格式时也一样：推荐项放第一个 option 且 label 加 ` (Recommended)`，
其余候选各占一个 option 并写 description。工具不可用时才退回文本，并说明原因。
