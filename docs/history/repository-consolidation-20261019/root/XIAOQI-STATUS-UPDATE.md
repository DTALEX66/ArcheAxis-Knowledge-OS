# 小栖图片资源状态更新

## 新发现 ✅

### 图片确实存在
```
frontend/src/assets/xiaoqi/
- idle.png (4.9MB)
- speaking.png (4.9MB)
- thinking.png (4.8MB)
```

### 但是...

#### 缺失的状态图片 ❌
前端代码期望5个状态：
```typescript
xiaoqi: {
  idle: ✅ 存在
  thinking: ✅ 存在
  speaking: ✅ 存在
  listening: ❌ 缺失
  completed: ❌ 缺失
}
```

#### 可用的源图片
`assets/astryn-full/assets/character/upgraded/v1/derived-alpha/` 中有：
- xiaoqi_state_completed_sleepwear_v1.png
- xiaoqi_state_failed_sleepwear_v1.png
- xiaoqi_state_thinking_sleepwear_v1.png
- xiaoqi_pose_listening_sleepwear_v1.png

## 需要做的

1. 复制 listening 图片
2. 复制 completed 图片
3. 测试前端加载
4. 验证状态切换

## 真实状态

**小栖显示**: ⚠️ 部分可用（3/5状态）

---
验证时间: 2026-10-16 23:22
