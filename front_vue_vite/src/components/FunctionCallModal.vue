<template>
    <div class="modal" @click.self="$emit('close')">
        <div class="modal-content function-call-modal">
            <div class="modal-header">
                <h3 class="modal-title">工具执行确认</h3>
                <button class="close-btn" @click="$emit('close')" title="关闭">×</button>
            </div>
            <div class="modal-body">
                <div class="tool-info">
                    <div class="tool-name">
                        <span class="label">工具名称：</span>
                        <span class="value">{{ functionCall.display_name || functionCall.name }}</span>
                    </div>
                    <div class="tool-desc">
                        <span class="label">描述：</span>
                        <span class="value">{{ functionCall.description }}</span>
                    </div>
                    <div class="tool-params" v-if="functionCall.params && Object.keys(functionCall.params).length > 0">
                        <span class="label">参数：</span>
                        <pre class="params-value">{{ JSON.stringify(functionCall.params, null, 2) }}</pre>
                    </div>
                </div>
                <div class="code-preview">
                    <div class="code-header">
                        <span>即将执行的代码：</span>
                        <button class="toggle-code-btn" @click="showCode = !showCode">
                            {{ showCode ? '收起代码' : '展开代码' }}
                        </button>
                    </div>
                    <pre class="code-content" v-if="showCode"><code>{{ functionCall.code }}</code></pre>
                </div>
                <div class="warning-text">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M8 1L15 14H1L8 1Z" stroke="#f59e0b" stroke-width="1.5" fill="none"/>
                        <line x1="8" y1="6" x2="8" y2="9" stroke="#f59e0b" stroke-width="1.5"/>
                        <circle cx="8" cy="11.5" r="0.75" fill="#f59e0b"/>
                    </svg>
                    <span>请确认是否允许执行此工具代码？</span>
                </div>
            </div>
            <div class="modal-buttons">
                <button class="cancel-btn" @click="$emit('close')">拒绝</button>
                <button class="confirm-btn" @click="handleConfirm" :disabled="isExecuting">
                    {{ isExecuting ? '执行中...' : '允许执行' }}
                </button>
            </div>
            <div class="execution-result" v-if="executionResult">
                <div class="result-header" :class="{ success: executionResult.success, error: !executionResult.success }">
                    {{ executionResult.success ? '执行成功' : '执行失败' }}
                </div>
                <pre class="result-content">{{ executionResult.stdout || executionResult.stderr || executionResult.error }}</pre>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
    functionCall: {
        type: Object,
        required: true
    }
});

const emit = defineEmits(['close', 'confirm']);

const showCode = ref(false);
const isExecuting = ref(false);
const executionResult = ref(null);

const handleConfirm = async () => {
    isExecuting.value = true;
    executionResult.value = null;
    
    try {
        const response = await fetch('http://localhost:8888/api/tools/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                tool_name: props.functionCall.name,
                params: props.functionCall.params || {}
            })
        });
        
        if (response.ok) {
            executionResult.value = await response.json();
            emit('confirm', executionResult.value);
        } else {
            executionResult.value = {
                success: false,
                error: '请求失败'
            };
        }
    } catch (error) {
        executionResult.value = {
            success: false,
            error: error.message
        };
    } finally {
        isExecuting.value = false;
    }
};
</script>

<style scoped>
.function-call-modal {
    max-width: 700px;
    max-height: 80vh;
    overflow-y: auto;
}

.modal-body {
    padding: 16px 0;
}

.tool-info {
    margin-bottom: 16px;
}

.tool-info .tool-name,
.tool-info .tool-desc,
.tool-info .tool-params {
    margin-bottom: 12px;
}

.tool-info .label {
    color: #94a3b8;
    font-size: 13px;
    display: block;
    margin-bottom: 4px;
}

.tool-info .value {
    color: #f8fafc;
    font-size: 14px;
}

.params-value {
    background: #1e293b;
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    color: #e2e8f0;
    overflow-x: auto;
    margin: 0;
}

.code-preview {
    margin-bottom: 16px;
}

.code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.code-header span {
    color: #94a3b8;
    font-size: 13px;
}

.toggle-code-btn {
    background: transparent;
    border: 1px solid #475569;
    color: #94a3b8;
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
}

.toggle-code-btn:hover {
    border-color: #38bdf8;
    color: #38bdf8;
}

.code-content {
    background: #0f172a;
    padding: 16px;
    border-radius: 8px;
    font-size: 12px;
    color: #e2e8f0;
    overflow-x: auto;
    max-height: 300px;
    margin: 0;
    border: 1px solid #334155;
}

.code-content code {
    font-family: 'Consolas', 'Monaco', monospace;
}

.warning-text {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 12px 16px;
    border-radius: 8px;
    color: #fbbf24;
    font-size: 14px;
}

.modal-buttons {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    margin-top: 16px;
}

.cancel-btn {
    background: transparent;
    border: 1px solid #475569;
    color: #94a3b8;
    padding: 10px 24px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
}

.cancel-btn:hover {
    border-color: #ef4444;
    color: #ef4444;
}

.confirm-btn {
    background: linear-gradient(135deg, #38bdf8, #0ea5e9);
    border: none;
    color: white;
    padding: 10px 24px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;
}

.confirm-btn:hover:not(:disabled) {
    background: linear-gradient(135deg, #0ea5e9, #0284c7);
}

.confirm-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.execution-result {
    margin-top: 16px;
    border-top: 1px solid #334155;
    padding-top: 16px;
}

.result-header {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 8px;
    padding: 8px 12px;
    border-radius: 6px;
}

.result-header.success {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
}

.result-header.error {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
}

.result-content {
    background: #1e293b;
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    color: #e2e8f0;
    overflow-x: auto;
    max-height: 200px;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
}
</style>
