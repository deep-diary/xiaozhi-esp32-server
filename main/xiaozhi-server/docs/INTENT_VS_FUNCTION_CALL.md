# intent_llm 与 function_call 详细对比

## 一、核心概念

### intent_llm（意图识别LLM模式）

**工作原理**：在用户输入后，先使用一个独立的LLM进行意图识别，分析用户意图并决定是否需要调用工具。如果需要调用工具，返回function_call格式的JSON，然后执行工具，最后使用主LLM生成自然语言回复。

**流程图**：
```
用户输入 → 意图识别LLM → 判断是否需要工具 → 执行工具 → 主LLM生成回复
```

### function_call（函数调用模式）

**工作原理**：直接在主LLM对话时，如果LLM支持function calling，LLM会在生成回复的过程中自动决定是否需要调用工具。如果检测到需要调用工具，LLM会生成function call，执行工具后，LLM继续生成最终回复。

**流程图**：
```
用户输入 → 主LLM(支持function calling) → 自动决定调用工具 → 执行工具 → LLM继续生成回复
```

## 二、详细对比表

| 对比项 | intent_llm | function_call |
|--------|-----------|---------------|
| **处理步骤** | 3步：意图识别 → 工具执行 → LLM回复 | 2步：LLM处理(含工具调用) → 继续处理 |
| **LLM调用次数** | 2次（意图识别LLM + 主LLM） | 1次或多次（主LLM递归调用） |
| **响应延迟** | 较高（需要额外的意图识别步骤，通常+200-500ms） | 较低（无需额外步骤） |
| **成本** | 较高（需要额外的LLM调用） | 较低（只需主LLM调用） |
| **通用性** | 高（可以处理复杂的意图识别逻辑） | 中（依赖LLM的function calling能力） |
| **灵活性** | 高（可以自定义意图识别提示词和规则） | 中（依赖LLM的function calling实现） |
| **LLM要求** | 需要独立的意图识别LLM（可以是轻量级模型） | 需要主LLM支持function calling |
| **多工具调用** | 支持（可以返回多个function_call的数组） | 支持（LLM可以生成多个tool_calls） |
| **调试难度** | 中等（需要调试意图识别和主LLM两个环节） | 较低（只需调试主LLM） |
| **适用LLM** | 任何LLM（意图识别和主LLM可以不同） | 需要支持function calling的LLM |

## 三、代码实现对比

### intent_llm 实现流程

```python
# 1. 用户输入后，先进行意图识别
intent_result = await conn.intent.detect_intent(conn, dialogue.dialogue, text)
# intent_result: '{"function_call": {"name": "get_weather", "arguments": {"location": "北京"}}}'

# 2. 解析意图结果
intent_data = json.loads(intent_result)
if "function_call" in intent_data:
    function_name = intent_data["function_call"]["name"]
    
    # 3. 执行工具
    result = await conn.func_handler.handle_llm_function_call(conn, function_call_data)
    
    # 4. 使用主LLM生成回复
    if result.action == Action.REQLLM:
        llm_result = conn.intent.replyResult(result.result, original_text)
        # 通过TTS回复用户
```

### function_call 实现流程

```python
# 1. 直接调用主LLM，传入functions列表
llm_responses = self.llm.response_with_functions(
    self.session_id,
    self.dialogue.get_llm_dialogue_with_memory(memory_str),
    functions=functions  # 传入可用函数列表
)

# 2. LLM在生成过程中自动决定是否调用工具
for response in llm_responses:
    if "tool_calls" in response:
        # 3. 执行工具
        result = await self.func_handler.handle_llm_function_call(self, tool_call_data)
        
        # 4. 递归调用chat()，LLM继续生成回复
        if result.action == Action.REQLLM:
            self.chat(None, depth=depth + 1)
```

## 四、使用场景建议

### 推荐使用 intent_llm 的场景

1. **主LLM不支持function calling**
   - 您使用的LLM不支持function calling功能
   - 但您仍然希望实现工具调用功能

2. **需要复杂的意图识别逻辑**
   - 需要根据对话历史、上下文进行复杂判断
   - 需要自定义意图识别的提示词和规则
   - 例如：需要特殊处理"现在几点了"这样的基础信息查询

3. **需要独立的意图识别模型**
   - 希望使用更轻量级的模型进行意图识别以节省成本
   - 意图识别可以使用便宜的模型，主LLM使用高质量模型

4. **需要精确控制工具调用时机**
   - 需要根据特定规则决定是否调用工具
   - 需要处理特殊的意图识别逻辑（如result_for_context）

5. **需要支持多函数并行调用**
   - intent_llm可以返回多个function_call的数组
   - 适合"打开灯并且调高音量"这样的复合指令

### 推荐使用 function_call 的场景

1. **LLM支持function calling**
   - 使用的LLM（如ChatGLM、Doubao、OpenAI等）支持function calling功能
   - 希望利用LLM的原生function calling能力

2. **追求响应速度**
   - 希望减少延迟，提高响应速度
   - 不需要额外的意图识别步骤

3. **简化架构**
   - 希望简化系统架构，减少组件
   - 不需要独立的意图识别逻辑

4. **成本敏感**
   - 希望减少LLM调用次数以降低成本
   - 充分利用主LLM的能力

5. **LLM能力强**
   - 使用的LLMfunction calling能力很强
   - 可以准确判断何时需要调用工具

## 五、性能对比示例

### intent_llm 性能示例

```
用户输入: "北京天气怎么样？"
  ↓
意图识别LLM调用: 200ms
  ↓
识别结果: {"function_call": {"name": "get_weather", "arguments": {"location": "北京"}}}
  ↓
执行工具(get_weather): 300ms
  ↓
主LLM生成回复: 800ms
  ↓
总耗时: ~1300ms
```

### function_call 性能示例

```
用户输入: "北京天气怎么样？"
  ↓
主LLM处理(检测到需要调用get_weather): 600ms
  ↓
执行工具(get_weather): 300ms
  ↓
主LLM继续生成回复: 500ms
  ↓
总耗时: ~1400ms (但通常更快，因为LLM可以并行处理)
```

**注意**：实际性能取决于LLM响应速度、工具执行时间等因素。function_call通常更快，因为减少了意图识别的额外步骤。

## 六、配置示例

### intent_llm 配置

```yaml
selected_module:
  Intent: intent_llm

Intent:
  intent_llm:
    type: intent_llm
    # 独立的意图识别LLM（可以使用轻量级模型）
    llm: ChatGLMLLM
    functions:
      - get_weather
      - play_music
      - get_system_info
      - calculate
```

### function_call 配置

```yaml
selected_module:
  Intent: function_call
  LLM: ChatGLMLLM  # 需要支持function calling

Intent:
  function_call:
    type: function_call
    functions:
      - get_weather
      - play_music
      - get_system_info
      - calculate
      - process_text
```

## 七、特殊功能对比

### intent_llm 特殊功能

1. **result_for_context**
   - intent_llm可以识别基础信息查询（时间、日期等）
   - 返回`result_for_context`，直接从上下文构建回答
   - 无需调用工具，提高效率

2. **continue_chat**
   - 明确标识普通对话，不需要调用工具
   - 可以清理对话历史中的工具相关消息

3. **多函数并行调用**
   - 可以返回多个function_call的数组
   - 适合复合指令

### function_call 特殊功能

1. **原生function calling**
   - 利用LLM的原生function calling能力
   - 更自然的工具调用决策

2. **递归调用**
   - 支持深度递归调用（最多5层）
   - 工具执行结果可以继续触发新的工具调用

3. **流式响应**
   - 支持流式输出，降低延迟
   - 工具调用结果可以实时返回

## 八、迁移建议

### 从 intent_llm 迁移到 function_call

**前提条件**：
- 您的LLM支持function calling
- 您不需要复杂的意图识别逻辑

**迁移步骤**：
1. 确认LLM支持function calling
2. 修改配置：`selected_module.Intent: function_call`
3. 移除意图识别LLM配置（如果之前配置了独立的LLM）
4. 测试功能是否正常

### 从 function_call 迁移到 intent_llm

**前提条件**：
- 您需要更复杂的意图识别逻辑
- 您的LLM不支持function calling或function calling能力不足

**迁移步骤**：
1. 修改配置：`selected_module.Intent: intent_llm`
2. 配置意图识别LLM（可以使用轻量级模型）
3. 测试功能是否正常

## 九、常见问题

### Q1: 两种模式可以同时使用吗？

**A**: 不可以。只能选择一种模式。在`selected_module.Intent`中配置。

### Q2: 哪种模式更好？

**A**: 取决于您的需求：
- 如果LLM支持function calling且能力强，推荐`function_call`（更快、更简单）
- 如果需要复杂意图识别或LLM不支持function calling，使用`intent_llm`

### Q3: 可以混合使用吗？

**A**: 不可以。但您可以在配置中切换模式，重启服务器即可生效。

### Q4: 自定义插件在两种模式下都能使用吗？

**A**: 是的。自定义插件通过`@register_function`注册后，两种模式都可以使用。只需要在配置的`functions`列表中添加函数名即可。

### Q5: 性能差异有多大？

**A**: 通常`function_call`比`intent_llm`快200-500ms（减少了意图识别步骤）。但实际差异取决于：
- LLM响应速度
- 工具执行时间
- 网络延迟等因素

## 十、总结

| 特性 | intent_llm | function_call | 推荐 |
|------|-----------|---------------|------|
| **速度** | 较慢 | 较快 | function_call |
| **成本** | 较高 | 较低 | function_call |
| **灵活性** | 高 | 中 | intent_llm |
| **通用性** | 高 | 中 | intent_llm |
| **易用性** | 中 | 高 | function_call |

**最终建议**：
- **优先选择 function_call**：如果您的LLM支持function calling，这是更好的选择
- **使用 intent_llm**：如果您的LLM不支持function calling，或需要复杂的意图识别逻辑

两种模式都可以很好地支持自定义插件，选择哪种主要取决于您的LLM能力和需求。

