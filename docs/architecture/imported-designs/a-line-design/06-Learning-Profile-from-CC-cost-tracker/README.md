# CC cost-tracker → A 线 | 学习画像系统

## 文件位置：src/cost-tracker.ts（302 行）

追踪 LLM API 调用的 Token 消耗和费用，类比学习的"成本核算"。

## 关键函数

- getStoredSessionCosts() — 读取已存储的会话费用
- saveCurrentSessionCosts() — 保存当前会话费用
- formatTotalCost() — 格式化总费用
- addToTotalSessionCost() — 累加到总会话费用

## A 线迁移

| A 线子系统 | CC 映射 | 迁移方式 |
|-----------|---------|---------|
| 13. 学习画像 | 追踪模式 | 追踪知识点学习投入时间/次数 |
| 13. 学习画像 | saveCurrentSessionCosts | 保存每日学习画像 |
| 13. 学习画像 | formatTotalCost | 学习统计报表 |
| 13. 学习画像 | addToTotalSessionCost | 累加复习次数/正确率 |

### 数据结构参考

```python
class LearningProfile:
    daily_records: {
        "2026-06-25": {
            "subjects": ["Python", "Math"],
            "reviewed": 45, "new": 12,
            "accuracy": 0.78, "time_min": 35,
            "weak_points": ["recursion"]
        }
    }
    weekly_summary: str
    monthly_trend: str
```
