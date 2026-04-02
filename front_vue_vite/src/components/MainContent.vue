<template>
    <div class="main-content">
        <div class="chat-container" ref="chatContainer">
            <div v-if="loadingChatId" class="chat-loading">
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span class="loading-text">加载中...</span>
            </div>
            <div v-for="(message, index) in messages" :key="index" class="message" :class="message.role === 'user' ? 'user-message' : 'assistant-message'">
                <div class="message-content">
                    <template v-if="message.role === 'assistant'">
                        <template v-if="isLoading && (!message.content || message.content.includes('loading-dots')) && !hasDetails(message)">
                            <div class="loading-dots">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </template>
                        <template v-else>
                            <template v-if="hasDetails(message)">
                                <button 
                                    type="button"
                                    class="toggle-details-btn" 
                                    :class="message.detailsExpanded ? 'expanded' : 'collapsed'"
                                    @click="toggleDetails(index); $event.preventDefault()"
                                >
                                    <span class="arrow">▼</span>
                                    <span class="text">{{ message.detailsExpanded ? '收起详情' : '展开详情' }}</span>
                                </button>
                                <div class="collapsible-content" :class="message.detailsExpanded ? 'visible' : 'hidden'">
                                    <template v-if="message.outputParts && message.outputParts.length > 0">
                                        <template v-for="(part, partIndex) in message.outputParts" :key="partIndex">
                                            <div v-if="part.type === 'reasoning' && isValidReasoningContent(part.content)" class="reasoning-section">
                                                <div class="reasoning-title">深度思考</div>
                                                <div class="reasoning-content">{{ part.content }}<span v-if="message.showLoading" class="inline-loading-dots"><span></span><span></span><span></span></span></div>
                                            </div>
                                            <div v-if="part.type === 'search' && part.sources && part.sources.length > 0" class="search-sources-section">
                                                <div class="search-sources-title">搜索来源</div>
                                                <div class="search-sources-list">
                                                    <a v-for="(source, idx) in part.sources" :key="idx" :href="source.url" class="search-source-item" target="_blank">[{{ idx + 1 }}] {{ source.url }}</a>
                                                </div>
                                            </div>
                                        </template>
                                    </template>
                                    <template v-else>
                                        <div v-if="getReasoningContent(message)" class="reasoning-section">
                                            <div class="reasoning-title">深度思考</div>
                                            <div class="reasoning-content">{{ getReasoningContent(message) }}<span v-if="message.showLoading" class="inline-loading-dots"><span></span><span></span><span></span></span></div>
                                        </div>
                                        <div v-else-if="getSearchSources(message).length > 0" class="search-sources-section">
                                            <div class="search-sources-title">搜索来源</div>
                                            <div class="search-sources-list">
                                                <a v-for="(source, idx) in getSearchSources(message)" :key="idx" :href="source.url" class="search-source-item" target="_blank">[{{ source.index || idx + 1 }}] {{ source.url }}</a>
                                            </div>
                                            <span v-if="message.showLoading" class="inline-loading-dots"><span></span><span></span><span></span></span>
                                        </div>
                                    </template>
                                </div>
                            </template>
                            <div v-if="message.content || message.answer" class="answer-section">
                                <div class="answer-header">
                                    <div class="answer-title">回答</div>
                                </div>
                                <div class="answer-content">
                                    <MdPreview 
                                        v-if="message.content || message.answer" 
                                        :modelValue="message.content || message.answer" 
                                        v-bind="mdPreviewProps"
                                    />
                                    <span v-if="message.showLoading" class="inline-loading-dots"><span></span><span></span><span></span></span>
                                </div>
                            </div>
                            <div v-if="(message.content || message.answer) && !message.isStreaming" class="action-buttons-row">
                                <button v-if="canGenerateChart(message) && !message.chartImage && !message.generatingChart" class="generate-chart-btn" @click="requestGenerateChart(index, message)" title="生成图表">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M3 3v18h18"/>
                                        <path d="M18 17V9"/>
                                        <path d="M13 17V5"/>
                                        <path d="M8 17v-3"/>
                                    </svg>
                                    生成图表
                                </button>
                                <button v-if="canGenerateChart(message) && message.chartImage && !message.generatingChart" class="view-chart-btn" @click="toggleChartDisplay(message)" title="查看图表">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M3 3v18h18"/>
                                        <path d="M18 17V9"/>
                                        <path d="M13 17V5"/>
                                        <path d="M8 17v-3"/>
                                    </svg>
                                    {{ message.chartExpanded ? '收起图表' : '查看图表' }}
                                </button>
                                <button class="copy-btn" @click="copyText(message.content || message.answer)" title="复制回答">
                                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                        <rect x="2" y="2" width="10" height="10" stroke="white" stroke-width="1.5" fill="none" rx="2" />
                                        <rect x="4.5" y="4.5" width="9" height="9" fill="#475569" stroke="white" stroke-width="1.5" rx="2" />
                                    </svg>
                                </button>
                            </div>
                            <div v-if="message.generatingChart" class="chart-loading-section">
                                <div class="loading-dots">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                                <span>正在生成图表...</span>
                            </div>
                            <div v-if="message.chartImage && message.chartExpanded !== false" class="chart-display-section">
                                <div class="chart-image-container">
                                    <img :src="`data:image/${message.chartImage.image_format || 'png'};base64,${message.chartImage.image_base64}`" :alt="message.chartImage.symbol + ' 图表'" class="chart-image" />
                                </div>
                                <div class="chart-actions">
                                    <button class="download-chart-btn" @click="downloadChart(message.chartImage)">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                            <polyline points="7,10 12,15 17,10"/>
                                            <line x1="12" y1="15" x2="12" y2="3"/>
                                        </svg>
                                        下载图片
                                    </button>
                                </div>
                            </div>
                        </template>
                        <div v-if="message.functionCallRequest" class="function-call-request">
                            <div class="function-call-header">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                    <path d="M8 1L15 14H1L8 1Z" stroke="#f59e0b" stroke-width="1.5" fill="none"/>
                                    <line x1="8" y1="6" x2="8" y2="9" stroke="#f59e0b" stroke-width="1.5"/>
                                    <circle cx="8" cy="11.5" r="0.75" fill="#f59e0b"/>
                                </svg>
                                <span>工具执行请求</span>
                            </div>
                            <div class="function-call-body">
                                <div class="function-call-info">
                                    <span class="label">工具：</span>
                                    <span class="value">{{ message.functionCallRequest.display_name || message.functionCallRequest.name }}</span>
                                </div>
                                <div class="function-call-info">
                                    <span class="label">描述：</span>
                                    <span class="value">{{ message.functionCallRequest.description }}</span>
                                </div>
                                <div class="function-call-info" v-if="message.functionCallRequest.params && Object.keys(message.functionCallRequest.params).length > 0">
                                    <span class="label">参数：</span>
                                    <div class="params-editor">
                                        <div v-for="(paramInfo, key) in message.functionCallRequest.params" :key="key" class="param-item">
                                            <label class="param-label">{{ key }}</label>
                                            <span class="param-description" v-if="paramInfo.description">{{ paramInfo.description }}</span>
                                            <select
                                                v-if="paramInfo.enum && paramInfo.enum.length > 0"
                                                class="param-select"
                                                :value="message.editedParams ? message.editedParams[key] : paramInfo.value"
                                                @change="updateParam(message, key, $event.target.value, 'string')"
                                            >
                                                <option v-for="option in paramInfo.enum" :key="option" :value="option">
                                                    {{ paramInfo.enum_labels && paramInfo.enum_labels[option] ? paramInfo.enum_labels[option] : option }}
                                                </option>
                                            </select>
                                            <input 
                                                v-else-if="paramInfo.type === 'string' || paramInfo.type === 'number' || paramInfo.type === 'integer'"
                                                :type="paramInfo.type === 'number' || paramInfo.type === 'integer' ? 'number' : 'text'"
                                                class="param-input"
                                                :value="message.editedParams ? message.editedParams[key] : paramInfo.value"
                                                @input="updateParam(message, key, $event.target.value, paramInfo.type)"
                                                :placeholder="String(paramInfo.value || '')"
                                            />
                                            <input 
                                                v-else-if="paramInfo.type === 'boolean'"
                                                type="checkbox" 
                                                class="param-checkbox"
                                                :checked="message.editedParams ? message.editedParams[key] : paramInfo.value"
                                                @change="updateParam(message, key, $event.target.checked, 'boolean')"
                                            />
                                            <textarea
                                                v-else-if="paramInfo.type === 'object' || paramInfo.type === 'array'"
                                                class="param-textarea"
                                                :value="message.editedParams ? JSON.stringify(message.editedParams[key], null, 2) : JSON.stringify(paramInfo.value, null, 2)"
                                                @input="updateParam(message, key, $event.target.value, 'json')"
                                                rows="3"
                                            ></textarea>
                                            <input
                                                v-else
                                                type="text"
                                                class="param-input"
                                                :value="message.editedParams ? message.editedParams[key] : paramInfo.value"
                                                @input="updateParam(message, key, $event.target.value, 'string')"
                                                :placeholder="String(paramInfo.value || '')"
                                            />
                                            <span class="param-type-hint">({{ paramInfo.type }})</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="function-call-code">
                                    <div class="code-header">
                                        <span>执行代码：</span>
                                        <button class="toggle-code-btn" @click="toggleCode(index)">
                                            {{ message.showCode ? '收起' : '展开' }}
                                        </button>
                                    </div>
                                    <textarea 
                                        v-if="message.showCode" 
                                        class="code-editor"
                                        v-model="message.editedCode"
                                        :placeholder="message.functionCallRequest.code"
                                        rows="10"
                                    ></textarea>
                                </div>
                            </div>
                            <div class="function-call-actions">
                                <button class="reject-btn" @click="$emit('reject-function-call', index)">拒绝</button>
                                <button class="confirm-btn" @click="executeWithParams(index, message)">允许执行</button>
                            </div>
                        </div>
                    </template>
                    <template v-else>
                        {{ message.content }}
                    </template>
                </div>
            </div>
        </div>

        <div class="input-area">
            <div class="input-wrapper">
                <textarea
                    v-model="inputMessage"
                    class="message-input"
                    placeholder="输入消息..."
                    @keydown.enter.prevent="handleEnter"
                    @input="handleInput"
                    rows="1"
                    id="messageInput"
                    name="messageInput"
                ></textarea>
                <div class="input-buttons">
                    <div class="feature-buttons">
                        <button 
                            class="feature-btn" 
                            :class="{ active: features.deepThink }"
                            @click="$emit('toggle-feature', 'deepThink')"
                        >
                            深度思考
                        </button>
                        <button 
                            class="feature-btn" 
                            :class="{ active: features.streamOutput }"
                            @click="$emit('toggle-feature', 'streamOutput')"
                        >
                            流式输出
                        </button>
                        <button class="feature-btn" @click="$emit('open-tools-modal')">
                            选择工具
                        </button>
                        <button class="feature-btn" @click="$emit('open-system-prompt-modal')">
                            系统提示词
                        </button>
                    </div>
                    <button class="send-btn" @click="handleSend" title="发送消息">
                        <svg v-if="!isLoading" width="20" height="20" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <polygon points="2.5,3 14,8 2.5,13" fill="white" />
                            <polygon points="2.5,6 2.5,10 0.5,8" fill="white" />
                        </svg>
                        <svg v-else width="20" height="20" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect x="4" y="2.5" width="3" height="11" rx="1" fill="white" />
                            <rect x="9" y="2.5" width="3" height="11" rx="1" fill="white" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import { MdPreview } from 'md-editor-v3';
import 'md-editor-v3/lib/preview.css';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-dark.css';

const props = defineProps({
    messages: {
        type: Array,
        default: () => []
    },
    isLoading: {
        type: Boolean,
        default: false
    },
    systemPrompt: {
        type: String,
        default: ''
    },
    features: {
        type: Object,
        default: () => ({})
    },
    selectedTools: {
        type: Object,
        default: () => ({})
    },
    loadingChatId: {
        type: [String, Number],
        default: null
    }
});

const emit = defineEmits(['send-message', 'toggle-feature', 'open-tools-modal', 'open-system-prompt-modal', 'copy-text', 'execute-function-call', 'reject-function-call', 'generate-chart']);

const inputMessage = ref('');
const chatContainer = ref(null);

const extractJsonFromContent = (content) => {
    if (!content) return null;
    
    const jsonBlockRegex = /```json\s*([\s\S]*?)\s*```/;
    const match = content.match(jsonBlockRegex);
    
    if (match && match[1]) {
        try {
            return JSON.parse(match[1].trim());
        } catch (e) {
            console.error('解析JSON失败:', e);
        }
    }
    
    return null;
};

const canGenerateChart = (message) => {
    const content = message.content || message.answer || '';
    
    const jsonData = extractJsonFromContent(content);
    if (!jsonData) return false;
    
    if (jsonData.error) return false;
    if (jsonData.klines && Array.isArray(jsonData.klines) && jsonData.klines.length > 0) return true;
    if (jsonData.ticks && Array.isArray(jsonData.ticks) && jsonData.ticks.length > 0) return true;
    
    return false;
};

const requestGenerateChart = (index, message) => {
    emit('generate-chart', index, {
        message_id: message.id,
        chat_id: message.chat_id
    });
};

const toggleChartDisplay = (message) => {
    isScrollingEnabled = false;
    message.chartExpanded = message.chartExpanded === false ? true : false;
    nextTick(() => {
        isScrollingEnabled = true;
    });
};

const downloadChart = (chartImage) => {
    if (!chartImage || !chartImage.image_base64) return;
    
    const link = document.createElement('a');
    link.href = `data:image/${chartImage.image_format || 'png'};base64,${chartImage.image_base64}`;
    link.download = `${chartImage.symbol || 'chart'}_${chartImage.chart_type || 'chart'}_${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

const toggleCode = (index) => {
    if (props.messages[index]) {
        props.messages[index].showCode = !props.messages[index].showCode;
        if (props.messages[index].showCode && !props.messages[index].editedCode) {
            const message = props.messages[index];
            const strategyCodes = message.functionCallRequest.strategy_codes;
            if (strategyCodes) {
                const strategy = message.editedParams?.strategy || message.functionCallRequest.params?.strategy?.value;
                const strategyCode = strategyCodes[strategy];
                message.editedCode = strategyCode || message.functionCallRequest.code;
            } else {
                message.editedCode = message.functionCallRequest.code;
            }
        }
    }
};

const updateParam = (message, key, value, paramType = 'string') => {
    if (!message.editedParams) {
        const initialParams = {};
        for (const [k, v] of Object.entries(message.functionCallRequest.params)) {
            initialParams[k] = v.value;
        }
        message.editedParams = initialParams;
    }
    
    if (paramType === 'json') {
        try {
            message.editedParams[key] = JSON.parse(value);
        } catch (e) {
            message.editedParams[key] = value;
        }
    } else if (paramType === 'number' || paramType === 'integer') {
        const numValue = paramType === 'integer' ? parseInt(value) : parseFloat(value);
        message.editedParams[key] = isNaN(numValue) ? value : numValue;
    } else if (paramType === 'boolean') {
        message.editedParams[key] = value;
    } else {
        message.editedParams[key] = value;
    }
    
    if (key === 'strategy' && message.functionCallRequest.strategy_codes) {
        const strategyCode = message.functionCallRequest.strategy_codes[value];
        if (strategyCode) {
            message.editedCode = strategyCode;
        }
    }
};

const executeWithParams = (index, message) => {
    const request = { ...message.functionCallRequest };
    if (message.editedParams) {
        request.params = { ...message.editedParams };
    } else {
        const initialParams = {};
        for (const [k, v] of Object.entries(message.functionCallRequest.params)) {
            initialParams[k] = v.value;
        }
        request.params = initialParams;
    }
    if (message.editedCode && message.editedCode !== message.functionCallRequest.code) {
        request.code = message.editedCode;
    }
    emit('execute-function-call', index, request);
};

const mdPreviewProps = {
  theme: 'dark',
  language: 'zh-CN',
  katex,
  highlight: hljs,
  previewTheme: 'atom-one-dark',
  codeTheme: 'atom'
};

const hasDetails = (message) => {
    if (message.outputParts && message.outputParts.length > 0) {
        // 检查是否有有效的推理内容或搜索来源
        return message.outputParts.some(part => 
            (part.type === 'reasoning' && isValidReasoningContent(part.content)) ||
            (part.type === 'search' && part.sources && part.sources.length > 0)
        );
    }
    if (message.details) {
        let detailsArray = message.details;
        if (typeof message.details === 'string') {
            try {
                detailsArray = JSON.parse(message.details);
            } catch (e) {
                return false;
            }
        }
        if (Array.isArray(detailsArray)) {
            return detailsArray.some(item => 
                (item.type === 'reasoning' && isValidReasoningContent(item.content)) ||
                (item.type === 'search' && item.sources && item.sources.length > 0)
            );
        }
        if (isValidReasoningContent(message.details.reasoning) || (message.details.sources && message.details.sources.length > 0)) {
            return true;
        }
    }
    return false;
};

// 检查推理内容是否有效（不为"<think>\n"等）
const isValidReasoningContent = (content) => {
    if (!content) return false;
    const trimmedContent = content.trim();
    return trimmedContent !== '<think>' && trimmedContent !== '<think>\n' && trimmedContent !== '<think>';
};

const getReasoningContent = (message) => {
    if (message.details) {
        let detailsArray = message.details;
        if (typeof message.details === 'string') {
            try {
                detailsArray = JSON.parse(message.details);
            } catch (e) {
                const content = message.details.reasoning || '';
                return isValidReasoningContent(content) ? content : '';
            }
        }
        if (Array.isArray(detailsArray)) {
            const reasoningItem = detailsArray.find(item => item.type === 'reasoning');
            const content = reasoningItem?.content || '';
            return isValidReasoningContent(content) ? content : '';
        }
        const content = message.details.reasoning || '';
        return isValidReasoningContent(content) ? content : '';
    }
    return '';
};

const getSearchSources = (message) => {
    if (message.details) {
        let detailsArray = message.details;
        if (typeof message.details === 'string') {
            try {
                detailsArray = JSON.parse(message.details);
            } catch (e) {
                return message.details.sources || [];
            }
        }
        if (Array.isArray(detailsArray)) {
            const searchItem = detailsArray.find(item => item.type === 'search');
            return searchItem?.sources || [];
        }
        return message.details.sources || [];
    }
    return [];
};

const toggleDetails = (index) => {
    if (props.messages[index]) {
        isScrollingEnabled = false;
        props.messages[index].detailsExpanded = !props.messages[index].detailsExpanded;
        nextTick(() => {
            isScrollingEnabled = true;
        });
    }
};

let isScrollingEnabled = true;

const scrollToBottom = () => {
    nextTick(() => {
        if (chatContainer.value && isScrollingEnabled) {
            chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
        }
    });
};

watch(() => props.messages, () => {
    if (isScrollingEnabled) {
        scrollToBottom();
    }
}, { deep: true });

watch(() => props.isLoading, () => {
    if (isScrollingEnabled) {
        scrollToBottom();
    }
});

const handleSend = () => {
    if (props.isLoading) {
        emit('send-message', '', '');
        return;
    }
    
    const message = inputMessage.value.trim();
    console.log('handleSend 被调用，message:', message);
    if (!message) return;

    const modelSelect = document.getElementById('modelSelect');
    const model = modelSelect ? modelSelect.value : 'qwen';
    console.log('选择的模型:', model);

    emit('send-message', message, model);
    inputMessage.value = '';
};

const handleInput = (event) => {
    const textarea = event.target;
    adjustTextareaHeight(textarea);
};

const handleEnter = (event) => {
    if (!event.shiftKey) {
        handleSend();
    } else {
        // Shift+Enter 换行
        event.preventDefault();
        const textarea = event.target;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        inputMessage.value = inputMessage.value.substring(0, start) + '\n' + inputMessage.value.substring(end);
        // 重新设置光标位置
        nextTick(() => {
            textarea.selectionStart = textarea.selectionEnd = start + 1;
            adjustTextareaHeight(textarea);
        });
    }
};

const adjustTextareaHeight = (textarea) => {
    // 重置高度以获取正确的scrollHeight
    textarea.style.height = 'auto';
    // 设置新高度
    const maxHeight = 300; // 最大高度
    const newHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = newHeight + 'px';
    // 当内容超过最大高度时，确保滚动条可见
    if (textarea.scrollHeight > maxHeight) {
        textarea.style.overflowY = 'auto';
    } else {
        textarea.style.overflowY = 'hidden';
    }
};

const copyText = (text) => {
    navigator.clipboard.writeText(text).then(() => {
        alert('复制成功');
    }).catch(err => {
        console.error('复制失败:', err);
    });
};
</script>

<style scoped>
.function-call-request {
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}

.function-call-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #fbbf24;
    font-weight: 500;
    margin-bottom: 12px;
    font-size: 14px;
}

.function-call-body {
    margin-bottom: 12px;
}

.function-call-info {
    margin-bottom: 8px;
}

.function-call-info .label {
    color: #94a3b8;
    font-size: 13px;
}

.function-call-info .value {
    color: #f8fafc;
    font-size: 13px;
}

.params-value {
    background: #1e293b;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    color: #e2e8f0;
    overflow-x: auto;
    margin: 4px 0 0 0;
}

.params-editor {
    background: #1e293b;
    padding: 12px;
    border-radius: 6px;
    margin: 4px 0 0 0;
}

.param-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

.param-item:last-child {
    margin-bottom: 0;
}

.param-label {
    color: #38bdf8;
    font-size: 12px;
    font-weight: 500;
    min-width: 80px;
}

.param-description {
    color: #94a3b8;
    font-size: 11px;
    margin-left: 8px;
    flex: 1;
}

.param-input {
    flex: 1;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 6px 10px;
    color: #e2e8f0;
    font-size: 12px;
    outline: none;
    transition: border-color 0.2s;
}

.param-input:focus {
    border-color: #38bdf8;
}

.param-input::placeholder {
    color: #64748b;
}

.param-checkbox {
    width: 16px;
    height: 16px;
    cursor: pointer;
    accent-color: #38bdf8;
}

.param-textarea {
    flex: 1;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 6px 10px;
    color: #e2e8f0;
    font-size: 12px;
    font-family: 'Consolas', 'Monaco', monospace;
    outline: none;
    resize: vertical;
    min-height: 60px;
    transition: border-color 0.2s;
}

.param-textarea:focus {
    border-color: #38bdf8;
}

.param-type-hint {
    color: #64748b;
    font-size: 11px;
    font-style: italic;
}

.function-call-code {
    margin-top: 12px;
}

.function-call-code .code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.function-call-code .code-header span {
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
    padding: 12px;
    border-radius: 6px;
    font-size: 11px;
    color: #e2e8f0;
    overflow-x: auto;
    max-height: 200px;
    margin: 0;
    border: 1px solid #334155;
}

.code-content code {
    font-family: 'Consolas', 'Monaco', monospace;
}

.code-editor {
    width: 100%;
    background: #0f172a;
    padding: 12px;
    border-radius: 6px;
    font-size: 11px;
    color: #e2e8f0;
    border: 1px solid #334155;
    font-family: 'Consolas', 'Monaco', monospace;
    resize: vertical;
    min-height: 150px;
    outline: none;
}

.code-editor:focus {
    border-color: #38bdf8;
}

.function-call-actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
}

.reject-btn {
    background: transparent;
    border: 1px solid #475569;
    color: #94a3b8;
    padding: 8px 20px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
}

.reject-btn:hover {
    border-color: #ef4444;
    color: #ef4444;
}

.confirm-btn {
    background: linear-gradient(135deg, #38bdf8, #0ea5e9);
    border: none;
    color: white;
    padding: 8px 20px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
}

.confirm-btn:hover {
    background: linear-gradient(135deg, #0ea5e9, #0284c7);
}

.action-buttons-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 12px;
}

.generate-chart-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, #10b981, #059669);
    border: none;
    color: white;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.2s;
}

.generate-chart-btn:hover {
    background: linear-gradient(135deg, #059669, #047857);
    transform: translateY(-1px);
}

.view-chart-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: transparent;
    border: 1px solid #10b981;
    color: #10b981;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.2s;
}

.view-chart-btn:hover {
    background: rgba(16, 185, 129, 0.1);
}

.chart-loading-section {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 12px;
    padding: 16px;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 8px;
    color: #10b981;
    font-size: 14px;
}

.chart-display-section {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid #334155;
}

.chart-image-container {
    background: #1a1a1a;
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 12px;
    overflow: hidden;
}

.chart-image {
    width: 100%;
    max-width: 100%;
    height: auto;
    border-radius: 4px;
}

.chart-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}

.download-chart-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: transparent;
    border: 1px solid #475569;
    color: #94a3b8;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
}

.download-chart-btn:hover {
    border-color: #38bdf8;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
}
</style>