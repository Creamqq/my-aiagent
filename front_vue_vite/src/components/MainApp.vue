<template>
    <div class="container">
        <Sidebar 
            v-if="currentView === 'main'"
            :user="user"
            :chat-history="chatHistory"
            :active-chat-id="activeChatId"
            :models="models"
            :loading-chat-id="loadingChatId"
            @new-chat="createNewChat"
            @switch-chat="switchChat"
            @delete-chat="showDeleteChatConfirm"
            @open-api-manager="showApiManagerModal = true"
            @open-game-modal="showGameModal = true"
            @logout="handleLogout"
            @update-chat-title="updateChatTitle"
        />
        <FinanceSidebar
            v-if="currentView === 'finance'"
            :user="user"
            :chat-history="financeChatHistory"
            :active-chat-id="financeActiveChatId"
            :models="models"
            :loading-chat-id="financeLoadingChatId"
            :default-model-name="financeDefaultModel"
            @new-chat="createFinanceChat"
            @switch-chat="switchFinanceChat"
            @delete-chat="showDeleteFinanceChatConfirm"
            @back="currentView = 'main'"
            @update-chat-title="updateFinanceChatTitle"
            @open-api-manager="showApiManagerModal = true"
            @open-account-settings="openAccountSettings"
        />
        <MainContent
            v-if="currentView === 'main'"
            :messages="currentMessages"
            :is-loading="isLoading"
            :system-prompt="systemPrompt"
            :features="features"
            :selected-tools="selectedTools"
            :loading-chat-id="loadingChatId"
            @send-message="sendMessage"
            @toggle-feature="toggleFeature"
            @open-tools-modal="showToolsModal = true"
            @open-system-prompt-modal="showSystemPromptModal = true"
            @copy-text="copyText"
            @execute-function-call="executeFunctionCall"
            @reject-function-call="rejectFunctionCall"
            @generate-chart="generateChart"
        />
        <FinanceAssistantMainContent
            v-if="currentView === 'finance'"
            :messages="financeMessages"
            :is-loading="isLoading"
            :system-prompt="financeSystemPrompt"
            :features="features"
            :selected-tools="selectedTools"
            :loading-chat-id="financeLoadingChatId"
            @send-message="sendFinanceMessage"
            @toggle-feature="toggleFeature"
            @open-tools-modal="showToolsModal = true"
            @open-system-prompt-modal="showFinanceSystemPromptModal = true"
            @copy-text="copyText"
            @execute-function-call="executeFunctionCall"
            @reject-function-call="rejectFunctionCall"
            @generate-chart="generateChart"
        />
        
        <SystemPromptModal
            v-if="showSystemPromptModal"
            :system-prompt="systemPrompt"
            @close="showSystemPromptModal = false"
            @save="saveSystemPrompt"
        />
        <SystemPromptModal
            v-if="showFinanceSystemPromptModal"
            :system-prompt="financeSystemPrompt"
            @close="showFinanceSystemPromptModal = false"
            @save="saveFinanceSystemPrompt"
        />
        
        <ToolsModal
            v-if="showToolsModal"
            :selected-tools="selectedTools"
            @close="showToolsModal = false"
            @save="saveTools"
        />
        
        <ApiManagerModal
            v-if="showApiManagerModal"
            :user-id="userId"
            @close="showApiManagerModal = false"
            @refresh-models="loadModels"
        />
        
        <DeleteChatModal
            v-if="showDeleteChatModal"
            @close="showDeleteChatModal = false"
            @confirm="confirmDeleteChat"
            @dont-ask-again="handleDontAskAgain"
        />
        
        <GameModal
            v-if="showGameModal"
            @close="showGameModal = false"
            @select-game="handleGameSelect"
        />
        
        <KuaiqiAccountModal
            v-if="showKuaiqiAccountModal"
            :kuaiqi-account="kuaiqiAccount"
            :has-password="hasKuaiqiPassword"
            :show-skip="kuaiqiModalShowSkip"
            @close="showKuaiqiAccountModal = false"
            @save="saveKuaiqiAccount"
            @skip="handleSkipKuaiqiAccount"
        />
    </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import Sidebar from './Sidebar.vue';
import MainContent from './MainContent.vue';
import SystemPromptModal from './SystemPromptModal.vue';
import ToolsModal from './ToolsModal.vue';
import ApiManagerModal from './ApiManagerModal.vue';
import DeleteChatModal from './DeleteChatModal.vue';
import GameModal from './GameModal.vue';
import FinanceAssistantMainContent from './FinanceAssistantMainContent.vue';
import FinanceSidebar from './FinanceSidebar.vue';
import KuaiqiAccountModal from './KuaiqiAccountModal.vue';
import financeTools from '../financeTools.js';

const props = defineProps({
    user: {
        type: Object,
        default: null
    }
});

console.log('MainApp 接收到的用户数据:', props.user);

const emit = defineEmits(['logout']);

const userId = ref('');
const chatHistory = ref([]);
const activeChatId = ref(null);
const currentMessages = ref([]);
const systemPrompt = ref("你是一个教学智能体，专注于帮助学生解决学习问题，提供详细的解释和指导。");
const features = ref({
    deepThink: false,
    streamOutput: true,
    webSearch: true
});
const selectedTools = ref({
    web_search: true,
    web_extractor: false,
    code_interpreter: false,
    web_search_image: false,
    image_search: false,
    file_search: false,
    mcp: false
});
const isLoading = ref(false);
const showSystemPromptModal = ref(false);
const showFinanceSystemPromptModal = ref(false);
const showToolsModal = ref(false);
const showApiManagerModal = ref(false);
const showDeleteChatModal = ref(false);
const showGameModal = ref(false);
const chatToDeleteId = ref(null);
const chatToDeleteType = ref('main');
const abortController = ref(null);
const models = ref([]);
const loadingChatId = ref(null);
const currentView = ref('main');

const financeChatHistory = ref([]);
const financeActiveChatId = ref(null);
const financeMessages = ref([]);
const financeLoadingChatId = ref(null);
const financeSystemPrompt = ref("你是一个专业的金融助手，专注于提供金融分析、投资建议、市场解读等服务。请用专业但易懂的方式回答用户的问题。");
const financeDefaultModel = ref(null);
const showKuaiqiAccountModal = ref(false);
const kuaiqiAccount = ref('');
const hasKuaiqiPassword = ref(false);
const kuaiqiAccountPrompted = ref(false);
const kuaiqiModalShowSkip = ref(true);

const generateUserId = () => {
    const id = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('agent_user_id', id);
    return id;
};

const initUserId = () => {
    console.log('初始化用户ID，props.user:', props.user);
    
    // 处理两种情况：直接的用户对象或包含user字段的响应对象
    const user = props.user && props.user.user ? props.user.user : props.user;
    
    if (user && user.user_id) {
        userId.value = user.user_id;
        console.log('使用登录用户的ID:', userId.value);
    } else {
        const storedId = localStorage.getItem('agent_user_id');
        if (storedId) {
            userId.value = storedId;
            console.log('使用存储的用户ID:', userId.value);
        } else {
            userId.value = generateUserId();
            console.log('生成新的用户ID:', userId.value);
        }
    }
};

const loadChatHistory = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        console.log('加载对话历史，用户ID:', user_id);
        const response = await fetch(`http://localhost:8888/api/chats?user_id=${encodeURIComponent(user_id)}`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        console.log('对话历史响应状态:', response.status);
        if (response.ok) {
            const data = await response.json();
            console.log('对话历史数据:', data);
            chatHistory.value = data.chats.map(chat => ({
                id: chat.id,
                title: chat.title,
                messages: []
            }));
            console.log('处理后的对话历史:', chatHistory.value);
            return true;
        } else {
            console.error('对话历史响应失败:', response.status);
        }
    } catch (error) {
        console.error('加载聊天历史失败:', error);
    }
    return false;
};

const loadModels = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        console.log('加载模型列表，用户ID:', user_id);
        const response = await fetch(`http://localhost:8888/api/model-configs?user_id=${encodeURIComponent(user_id)}`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        console.log('模型列表响应状态:', response.status);
        if (response.ok) {
            const data = await response.json();
            console.log('模型列表数据:', data);
            models.value = data.models || [];
            console.log('处理后的模型列表:', models.value);
            
            // 自动选择默认模型
            setTimeout(() => {
                const defaultModel = models.value.find(model => model.isDefault);
                if (defaultModel) {
                    const modelSelect = document.getElementById('modelSelect');
                    if (modelSelect) {
                        modelSelect.value = defaultModel.name;
                        console.log('已自动选择默认模型:', defaultModel.name);
                    }
                }
            }, 100);
        } else {
            console.error('模型列表响应失败:', response.status);
        }
    } catch (error) {
        console.error('加载模型列表失败:', error);
    }
};

const loadSystemPrompt = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        console.log('加载系统提示词，用户ID:', user_id);
        const response = await fetch(`http://localhost:8888/api/system-prompt?user_id=${encodeURIComponent(user_id)}`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        console.log('系统提示词响应状态:', response.status);
        if (response.ok) {
            const data = await response.json();
            console.log('系统提示词数据:', data);
            systemPrompt.value = data.system_prompt;
            console.log('加载的系统提示词:', systemPrompt.value);
        } else {
            console.error('系统提示词响应失败:', response.status);
        }
    } catch (error) {
        console.error('加载系统提示词失败:', error);
    }
};

const createNewChat = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch('http://localhost:8888/api/chats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                user_id: user_id
            })
        });
        
        if (response.ok) {
            const chat = await response.json();
            chatHistory.value.unshift({
                id: chat.id,
                title: chat.title,
                messages: []
            });
            await switchChat(chat.id);
        }
    } catch (error) {
        console.error('创建新聊天失败:', error);
    }
};

const switchChat = async (chatId) => {
    loadingChatId.value = chatId;
    activeChatId.value = chatId;
    currentMessages.value = [];
    
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch(`http://localhost:8888/api/chats/${chatId}?user_id=${encodeURIComponent(user_id)}`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        if (response.ok) {
            const chatData = await response.json();
            
            await nextTick();
            currentMessages.value = chatData.messages.map(msg => {
                let outputParts = [];
                let detailsObj = null;
                
                if (msg.details) {
                    let detailsArray = msg.details;
                    if (typeof msg.details === 'string') {
                        try {
                            detailsArray = JSON.parse(msg.details);
                        } catch (e) {
                            detailsArray = null;
                        }
                    }
                    
                    if (Array.isArray(detailsArray)) {
                        outputParts = detailsArray.map(item => {
                            if (item.type === 'reasoning') {
                                return {
                                    type: 'reasoning',
                                    content: item.content
                                };
                            } else if (item.type === 'search') {
                                return {
                                    type: 'search',
                                    sources: item.sources || [],
                                    status: 'completed'
                                };
                            } else if (item.type === 'tool_execution') {
                                return {
                                    type: 'tool_execution',
                                    process: item.process
                                };
                            }
                            return null;
                        }).filter(p => p !== null);
                        
                        detailsObj = {
                            reasoning: detailsArray.find(d => d.type === 'reasoning')?.content || '',
                            sources: detailsArray.find(d => d.type === 'search')?.sources || []
                        };
                    }
                }
                
                const messageObj = {
                    id: msg.id,
                    chat_id: msg.chat_id || chatId,
                    role: msg.role,
                    content: msg.content,
                    details: detailsObj,
                    outputParts: outputParts,
                    detailsExpanded: true,
                    isStreaming: false
                };
                
                if (msg.chart) {
                    messageObj.chartImage = msg.chart;
                    messageObj.chartExpanded = false;
                }
                
                return messageObj;
            });
        }
    } catch (error) {
        console.error('加载对话消息失败:', error);
        currentMessages.value = [];
    } finally {
        loadingChatId.value = null;
    }
};

const sendMessage = async (content, model) => {
    console.log('sendMessage 被调用，content:', content, 'model:', model);
    
    // 如果正在发送，取消发送
    if (isLoading.value) {
        if (abortController.value) {
            abortController.value.abort();
        }
        isLoading.value = false;
        abortController.value = null;
        return;
    }

    if (!activeChatId.value) {
        await createNewChat();
    }

    const userMessage = {
        role: 'user',
        content: content
    };

    currentMessages.value.push(userMessage);
    console.log('添加用户消息后，currentMessages:', JSON.stringify(currentMessages.value));

    isLoading.value = true;
    abortController.value = new AbortController();

    const loadingMessage = {
        role: 'assistant',
        content: '',
        showLoading: false,
        isSearching: false,
        isStreaming: true,
        details: {
            reasoning: '',
            sources: []
        },
        outputParts: [],
        detailsExpanded: true
    };
    currentMessages.value.push(loadingMessage);
    console.log('添加 loading 消息后，currentMessages:', JSON.stringify(currentMessages.value));

    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        
        const currentChat = chatHistory.value.find(c => c.id === activeChatId.value);
        if (!currentChat) {
            throw new Error('当前对话不存在');
        }
        
        const messages = [
            { role: 'system', content: systemPrompt.value },
            ...currentMessages.value.filter(msg => msg.role !== 'system' && msg.content && msg.content.trim() !== '').map(msg => ({
                role: msg.role,
                content: msg.content
            }))
        ];
        
        console.log('构建的 messages:', JSON.stringify(messages));
        
        let tools = [];
        if (selectedTools.value.web_search) tools.push({ type: "web_search" });
        if (selectedTools.value.web_extractor) tools.push({ type: "web_extractor" });
        if (selectedTools.value.code_interpreter) tools.push({ type: "code_interpreter" });
        if (selectedTools.value.web_search_image) tools.push({ type: "web_search_image" });
        if (selectedTools.value.image_search) tools.push({ type: "image_search" });
        if (selectedTools.value.file_search) {
            tools.push({ 
                type: "file_search",
                vector_store_ids: ["your_knowledge_base_id"]
            });
        }
        if (selectedTools.value.mcp) {
            tools.push({
                type: "mcp",
                server_protocol: "sse",
                server_label: "amap-maps",
                server_description: "高德地图MCP Server现已覆盖15大核心接口，提供全场景覆盖的地理信息服务",
                server_url: "https://dashscope.aliyuncs.com/api/v1/mcps/amap-maps/sse",
                headers: {
                    "Authorization": "Bearer <your-mcp-server-token>"
                }
            });
        }
        
        const requestData = {
            model: model,
            messages: messages,
            temperature: 0.7,
            stream: features.value.streamOutput,
            top_p: 1.0,
            instructions: systemPrompt.value,
            tools: tools.length > 0 ? tools : undefined,
            tool_choice: tools.length > 0 ? "auto" : null,
            enable_thinking: features.value.deepThink,
            conversation: `chat_${activeChatId.value}`,
            user_id: user_id
        };
        
        const response = await fetch('http://localhost:8888/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify(requestData),
            signal: abortController.value.signal
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'API请求失败');
        }
        
        if (features.value.streamOutput) {
            await handleStreamResponse(response);
        } else {
            await handleNormalResponse(response);
        }
        
        await refreshChatTitle();
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('发送消息错误:', error);
            currentMessages.value.push({
                role: 'assistant',
                content: '抱歉，发送消息时出现错误，请稍后重试。'
            });
        } else {
            // 非流式输出模式下显示"已暂停"
            if (!features.value.streamOutput) {
                const lastMessage = currentMessages.value[currentMessages.value.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = '已暂停';
                }
            }
        }
    } finally {
        isLoading.value = false;
        abortController.value = null;
    }
};

const refreshChatTitle = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch(`http://localhost:8888/api/chats?user_id=${encodeURIComponent(user_id)}`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        if (response.ok) {
            const data = await response.json();
            data.chats.forEach(chat => {
                const existingChat = chatHistory.value.find(c => c.id === chat.id);
                if (existingChat) {
                    existingChat.title = chat.title;
                }
            });
        }
    } catch (error) {
        console.error('刷新对话标题失败:', error);
    }
};

const updateChatTitle = (updatedChat) => {
    const existingChat = chatHistory.value.find(c => c.id === updatedChat.id);
    if (existingChat) {
        existingChat.title = updatedChat.title;
    }
};

// 保存对话消息到后端
const saveChatMessages = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        
        // 构建要保存的消息数组
        // 过滤条件：非系统消息，且有内容（content、reasoning或sources）
        const messagesToSave = currentMessages.value.filter(msg => {
            if (msg.role === 'system') return false;
            
            // 检查是否有内容
            const hasContent = msg.content && msg.content.trim() !== '';
            const hasReasoning = msg.details?.reasoning && msg.details.reasoning.trim() !== '';
            const hasSources = msg.details?.sources && msg.details.sources.length > 0;
            const hasOutputParts = msg.outputParts && msg.outputParts.length > 0;
            
            return hasContent || hasReasoning || hasSources || hasOutputParts;
        }).map(msg => {
            // 构建 details 数组
            let detailsArray = [];
            if (msg.outputParts && msg.outputParts.length > 0) {
                msg.outputParts.forEach(part => {
                    if (part.type === 'reasoning' && part.content) {
                        detailsArray.push({
                            type: 'reasoning',
                            content: part.content
                        });
                    } else if (part.type === 'search' && part.sources && part.sources.length > 0) {
                        detailsArray.push({
                            type: 'search',
                            sources: part.sources.map((source, index) => ({
                                index: index + 1,
                                url: source.url || '#',
                                title: source.title || ''
                            }))
                        });
                    }
                });
            }
            
            return {
                role: msg.role,
                content: msg.content || '',
                details: detailsArray.length > 0 ? detailsArray : null
            };
        });
        
        const response = await fetch(`http://localhost:8888/api/chats/${activeChatId.value}?user_id=${encodeURIComponent(user_id)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                messages: messagesToSave
            })
        });
        
        if (!response.ok) {
            console.error('保存对话失败:', await response.json());
        } else {
            console.log('保存对话成功');
        }
    } catch (error) {
        console.error('保存对话失败:', error);
    }
};

const toggleFeature = (feature) => {
    features.value[feature] = !features.value[feature];
    if (feature === 'webSearch') {
        selectedTools.value.web_search = features.value.webSearch;
    }
};

const saveSystemPrompt = async (prompt) => {
    systemPrompt.value = prompt;
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        console.log('保存系统提示词，用户ID:', user_id);
        const response = await fetch(`http://localhost:8888/api/system-prompt?user_id=${encodeURIComponent(user_id)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                system_prompt: prompt
            })
        });
        console.log('保存系统提示词响应状态:', response.status);
        if (response.ok) {
            const data = await response.json();
            console.log('保存系统提示词成功:', data);
        } else {
            console.error('保存系统提示词失败:', response.status);
        }
    } catch (error) {
        console.error('保存系统提示词失败:', error);
    }
};

const saveFinanceSystemPrompt = async (prompt) => {
    financeSystemPrompt.value = prompt;
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        console.log('保存金融助手系统提示词，用户ID:', user_id);
        const response = await fetch(`http://localhost:8888/api/finance-config`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                user_id: user_id,
                system_prompt: prompt
            })
        });
        console.log('保存金融助手系统提示词响应状态:', response.status);
        if (response.ok) {
            const data = await response.json();
            console.log('保存金融助手系统提示词成功:', data);
        } else {
            console.error('保存金融助手系统提示词失败:', response.status);
        }
    } catch (error) {
        console.error('保存金融助手系统提示词失败:', error);
    }
};

const saveKuaiqiAccount = async ({ account, password }) => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch(`http://localhost:8888/api/finance-config`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                user_id: user_id,
                kuaiqi_account: account,
                kuaiqi_password: password
            })
        });
        if (response.ok) {
            const data = await response.json();
            kuaiqiAccount.value = data.kuaiqi_account || '';
            hasKuaiqiPassword.value = data.has_kuaiqi_password || false;
            showKuaiqiAccountModal.value = false;
            console.log('保存快期账户成功:', data);
        } else {
            console.error('保存快期账户失败:', response.status);
        }
    } catch (error) {
        console.error('保存快期账户失败:', error);
    }
};

const handleSkipKuaiqiAccount = () => {
    showKuaiqiAccountModal.value = false;
};

const handleFunctionCallConfirm = async (messageIndex, result) => {
    console.log('函数执行结果:', result);
    
    const messages = currentView.value === 'finance' ? financeMessages.value : currentMessages.value;
    const message = messages[messageIndex];
    const chatId = currentView.value === 'finance' ? financeActiveChatId.value : activeChatId.value;
    
    if (message) {
        message.isExecutingTool = false;
        if (result && result.success) {
            let content = '';
            if (result.result !== null && result.result !== undefined) {
                content = `✅ 执行结果:\n\`\`\`json\n${JSON.stringify(result.result, null, 2)}\n\`\`\``;
                message.toolResult = result.result;
            } else if (result.stdout) {
                content = `✅ 执行结果:\n\`\`\`\n${result.stdout}\n\`\`\``;
            }
            message.content = content || '执行成功';
            
            if (result.process_output) {
                message.details = JSON.stringify([{
                    type: 'tool_execution',
                    process: result.process_output
                }]);
            }
            
            await saveChatMessages();
            
            if (currentView.value === 'finance') {
                await switchFinanceChat(chatId);
            } else {
                await switchChat(chatId);
            }
        } else if (result && !result.success) {
            message.content = `❌ 工具执行失败: ${result.error || result.stderr || '未知错误'}`;
        }
        message.functionCallRequest = null;
    }
};

const executeFunctionCall = async (messageIndex, functionCallRequest) => {
    const user = props.user && props.user.user ? props.user.user : props.user;
    const user_id = user && user.user_id ? user.user_id : userId.value;
    const chatId = currentView.value === 'finance' ? financeActiveChatId.value : activeChatId.value;
    const messages = currentView.value === 'finance' ? financeMessages.value : currentMessages.value;
    const message = messages[messageIndex];
    
    if (message) {
        message.functionCallRequest = null;
        message.content = '⏳ 正在执行工具...\n';
        message.isExecutingTool = true;
    }
    
    let processOutput = '';
    let finalResult = null;
    const toolAbortController = new AbortController();
    const toolTimeoutId = setTimeout(() => {
        toolAbortController.abort();
        console.log('工具执行超时，已取消请求');
    }, 180000);
    
    const parseSSELine = (line) => {
        if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
                console.log('收到 [DONE] 信号');
                return;
            }
            
            try {
                const parsed = JSON.parse(data);
                console.log('收到 SSE 消息:', parsed.type, parsed);
                
                if (parsed.type === 'process_output') {
                    processOutput += parsed.line + '\n';
                    if (message) {
                        message.details = JSON.stringify([{
                            type: 'tool_execution',
                            process: processOutput
                        }]);
                        if (!message.outputParts) {
                            message.outputParts = [];
                        }
                        const existingToolPart = message.outputParts.find(p => p.type === 'tool_execution');
                        if (existingToolPart) {
                            existingToolPart.process = processOutput;
                        } else {
                            message.outputParts.push({
                                type: 'tool_execution',
                                process: processOutput
                            });
                        }
                        message.content = '⏳ 正在执行工具...';
                    }
                } else if (parsed.type === 'done') {
                    console.log('收到 done 消息, result:', parsed.result);
                    finalResult = parsed.result;
                    handleFunctionCallConfirm(messageIndex, {
                        success: parsed.success,
                        process_output: processOutput.trim(),
                        result: finalResult
                    });
                } else if (parsed.type === 'error') {
                    handleFunctionCallConfirm(messageIndex, {
                        success: false,
                        error: parsed.message
                    });
                }
            } catch (e) {
                console.error('解析响应失败:', e, data);
            }
        }
    };
    
    try {
        const response = await fetch('http://localhost:8888/api/tools/execute/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                tool_name: functionCallRequest.name,
                params: functionCallRequest.params || {},
                chat_id: chatId,
                user_id: user_id,
                code: functionCallRequest.code
            }),
            signal: toolAbortController.signal
        });
        
        if (!response.ok) {
            clearTimeout(toolTimeoutId);
            handleFunctionCallConfirm(messageIndex, { success: false, error: '请求失败' });
            return;
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                parseSSELine(line);
            }
            
            if (done) {
                if (buffer.trim()) {
                    parseSSELine(buffer);
                }
                break;
            }
        }
        clearTimeout(toolTimeoutId);
    } catch (error) {
        clearTimeout(toolTimeoutId);
        if (error.name === 'AbortError') {
            handleFunctionCallConfirm(messageIndex, { success: false, error: '工具执行超时（3分钟）' });
        } else {
            handleFunctionCallConfirm(messageIndex, { success: false, error: error.message });
        }
    }
};

const rejectFunctionCall = async (messageIndex) => {
    const messages = currentView.value === 'finance' ? financeMessages.value : currentMessages.value;
    const message = messages[messageIndex];
    const user = props.user && props.user.user ? props.user.user : props.user;
    const user_id = user && user.user_id ? user.user_id : userId.value;
    const chatId = currentView.value === 'finance' ? financeActiveChatId.value : activeChatId.value;
    
    if (message) {
        message.functionCallRequest = null;
        message.content = '用户拒绝了工具执行请求。';
        
        if (chatId) {
            try {
                await fetch(`http://localhost:8888/api/chats/${chatId}/messages?user_id=${user_id}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json; charset=utf-8'
                    },
                    body: JSON.stringify({
                        role: 'assistant',
                        content: '用户拒绝了工具执行请求。',
                        user_id: user_id
                    })
                });
            } catch (error) {
                console.error('保存拒绝消息失败:', error);
            }
        }
    }
};

const generateChart = async (messageIndex, chartRequest) => {
    const user = props.user && props.user.user ? props.user.user : props.user;
    const user_id = user && user.user_id ? user.user_id : userId.value;
    const chatId = currentView.value === 'finance' ? financeActiveChatId.value : activeChatId.value;
    const messages = currentView.value === 'finance' ? financeMessages.value : currentMessages.value;
    const message = messages[messageIndex];
    
    if (!message) return;
    
    message.generatingChart = true;
    
    try {
        let requestBody;
        
        if (chartRequest.message_id || message.id) {
            requestBody = {
                message_id: chartRequest.message_id || message.id,
                chat_id: chartRequest.chat_id || chatId,
                chart_type: 'candle',
                user_id: user_id
            };
        } else {
            requestBody = {
                chat_id: chatId,
                message_content: message.content || message.answer || '',
                chart_type: 'candle',
                user_id: user_id
            };
        }
        
        const response = await fetch('http://localhost:8888/api/charts/generate-from-message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '生成图表失败');
        }
        
        const result = await response.json();
        
        message.chartImage = {
            id: result.chart_id,
            symbol: result.symbol,
            chart_type: result.chart_type,
            duration_seconds: result.duration_seconds,
            image_base64: result.image_base64,
            image_format: result.image_format,
            data_count: result.data_count
        };
        message.chartGenerated = true;
        message.chartExpanded = true;
    } catch (error) {
        console.error('生成图表失败:', error);
        alert('生成图表失败: ' + error.message);
    } finally {
        message.generatingChart = false;
    }
};

const openAccountSettings = () => {
    kuaiqiModalShowSkip.value = false;
    showKuaiqiAccountModal.value = true;
};

const saveTools = (tools) => {
    selectedTools.value = tools;
};

const showDeleteChatConfirm = (chatId) => {
    const dontAskAgain = localStorage.getItem('agent_delete_chat_no_confirm');
    if (dontAskAgain === 'true') {
        deleteChat(chatId, 'main');
    } else {
        chatToDeleteId.value = chatId;
        chatToDeleteType.value = 'main';
        showDeleteChatModal.value = true;
    }
};

const confirmDeleteChat = () => {
    if (chatToDeleteId.value) {
        deleteChat(chatToDeleteId.value, chatToDeleteType.value);
    }
    showDeleteChatModal.value = false;
};

const handleDontAskAgain = (dontAsk) => {
    if (dontAsk) {
        localStorage.setItem('agent_delete_chat_no_confirm', 'true');
    } else {
        localStorage.removeItem('agent_delete_chat_no_confirm');
    }
};

const deleteChat = async (chatId, chatType = 'main') => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch(`http://localhost:8888/api/chats/${chatId}?user_id=${encodeURIComponent(user_id)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        
        if (response.ok) {
            if (chatType === 'finance') {
                financeChatHistory.value = financeChatHistory.value.filter(chat => chat.id !== chatId);
                if (financeActiveChatId.value === chatId) {
                    if (financeChatHistory.value.length > 0) {
                        await switchFinanceChat(financeChatHistory.value[0].id);
                    } else {
                        financeActiveChatId.value = null;
                        financeMessages.value = [];
                        await createFinanceChat();
                    }
                }
            } else {
                chatHistory.value = chatHistory.value.filter(chat => chat.id !== chatId);
                if (activeChatId.value === chatId) {
                    if (chatHistory.value.length > 0) {
                        await switchChat(chatHistory.value[0].id);
                    } else {
                        activeChatId.value = null;
                        currentMessages.value = [];
                        await createNewChat();
                    }
                }
            }
        }
    } catch (error) {
        console.error('删除对话失败:', error);
    }
};

const copyText = (text) => {
    navigator.clipboard.writeText(text).then(() => {
        alert('复制成功');
    }).catch(err => {
        console.error('复制失败:', err);
    });
};

const handleLogout = () => {
    localStorage.removeItem('agent_user_data');
    emit('logout');
};

const handleGameSelect = (gameType) => {
    console.log('选择了智能体:', gameType);
    if (gameType === 'finance') {
        currentView.value = 'finance';
        loadFinanceConfig();
        loadFinanceChatHistory();
    }
};

const loadFinanceConfig = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch(`http://localhost:8888/api/finance-config?user_id=${encodeURIComponent(user_id)}`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        if (response.ok) {
            const data = await response.json();
            if (data.system_prompt) {
                financeSystemPrompt.value = data.system_prompt;
            }
            if (data.default_model_name) {
                financeDefaultModel.value = data.default_model_name;
            } else {
                const defaultModel = models.value.find(model => model.isDefault);
                if (defaultModel) {
                    financeDefaultModel.value = defaultModel.name;
                } else if (models.value.length > 0) {
                    financeDefaultModel.value = models.value[0].name;
                }
            }
            kuaiqiAccount.value = data.kuaiqi_account || '';
            hasKuaiqiPassword.value = data.has_kuaiqi_password || false;
            
            if (!kuaiqiAccountPrompted.value && (!kuaiqiAccount.value || !hasKuaiqiPassword.value)) {
                kuaiqiModalShowSkip.value = true;
                showKuaiqiAccountModal.value = true;
                kuaiqiAccountPrompted.value = true;
            }
        }
    } catch (error) {
        console.error('加载金融助手配置失败:', error);
    }
};

const loadFinanceChatHistory = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch(`http://localhost:8888/api/chats?user_id=${encodeURIComponent(user_id)}&type=2`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        if (response.ok) {
            const data = await response.json();
            financeChatHistory.value = data.chats.map(chat => ({
                id: chat.id,
                title: chat.title,
                messages: []
            }));
        }
    } catch (error) {
        console.error('加载金融助手对话历史失败:', error);
    }
};

const createFinanceChat = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch('http://localhost:8888/api/chats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                user_id: user_id,
                type: 2
            })
        });
        
        if (response.ok) {
            const chat = await response.json();
            financeChatHistory.value.unshift({
                id: chat.id,
                title: chat.title,
                messages: []
            });
            await switchFinanceChat(chat.id);
        }
    } catch (error) {
        console.error('创建金融助手对话失败:', error);
    }
};

const switchFinanceChat = async (chatId) => {
    financeLoadingChatId.value = chatId;
    financeActiveChatId.value = chatId;
    financeMessages.value = [];
    
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch(`http://localhost:8888/api/chats/${chatId}?user_id=${encodeURIComponent(user_id)}`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        if (response.ok) {
            const chatData = await response.json();
            
            await nextTick();
            financeMessages.value = chatData.messages.map(msg => {
                let outputParts = [];
                let detailsObj = null;
                
                if (msg.details) {
                    let detailsArray = msg.details;
                    if (typeof msg.details === 'string') {
                        try {
                            detailsArray = JSON.parse(msg.details);
                        } catch (e) {
                            detailsArray = null;
                        }
                    }
                    
                    if (Array.isArray(detailsArray)) {
                        outputParts = detailsArray.map(item => {
                            if (item.type === 'reasoning') {
                                return {
                                    type: 'reasoning',
                                    content: item.content
                                };
                            } else if (item.type === 'search') {
                                return {
                                    type: 'search',
                                    sources: item.sources || [],
                                    status: 'completed'
                                };
                            } else if (item.type === 'tool_execution') {
                                return {
                                    type: 'tool_execution',
                                    process: item.process
                                };
                            }
                            return null;
                        }).filter(p => p !== null);
                        
                        detailsObj = {
                            reasoning: detailsArray.find(d => d.type === 'reasoning')?.content || '',
                            sources: detailsArray.find(d => d.type === 'search')?.sources || []
                        };
                    }
                }
                
                const messageObj = {
                    id: msg.id,
                    chat_id: msg.chat_id || chatId,
                    role: msg.role,
                    content: msg.content,
                    details: detailsObj,
                    outputParts: outputParts,
                    detailsExpanded: true,
                    isStreaming: false
                };
                
                if (msg.chart) {
                    messageObj.chartImage = msg.chart;
                    messageObj.chartExpanded = false;
                }
                
                return messageObj;
            });
        }
    } catch (error) {
        console.error('加载金融助手对话消息失败:', error);
        financeMessages.value = [];
    } finally {
        financeLoadingChatId.value = null;
    }
};

const showDeleteFinanceChatConfirm = (chatId) => {
    chatToDeleteId.value = chatId;
    chatToDeleteType.value = 'finance';
    showDeleteChatModal.value = true;
};

const updateFinanceChatTitle = (updatedChat) => {
    const existingChat = financeChatHistory.value.find(c => c.id === updatedChat.id);
    if (existingChat) {
        existingChat.title = updatedChat.title;
    }
};

const sendFinanceMessage = async (content, model) => {
    console.log('sendFinanceMessage 被调用，content:', content, 'model:', model);
    
    if (isLoading.value) {
        if (abortController.value) {
            abortController.value.abort();
        }
        isLoading.value = false;
        abortController.value = null;
        return;
    }

    if (!financeActiveChatId.value) {
        await createFinanceChat();
    }

    const userMessage = {
        role: 'user',
        content: content
    };

    financeMessages.value.push(userMessage);

    isLoading.value = true;
    abortController.value = new AbortController();

    const loadingMessage = {
        role: 'assistant',
        content: '',
        showLoading: false,
        isSearching: false,
        isStreaming: true,
        details: {
            reasoning: '',
            sources: []
        },
        outputParts: [],
        detailsExpanded: true
    };
    financeMessages.value.push(loadingMessage);

    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        
        const messages = [
            { role: 'system', content: financeSystemPrompt.value },
            ...financeMessages.value.filter(msg => msg.role !== 'system' && msg.content && msg.content.trim() !== '').map(msg => ({
                role: msg.role,
                content: msg.content
            }))
        ];
        
        let tools = [...financeTools];
        if (selectedTools.value.web_search) tools.push({ type: "web_search" });
        
        
        const requestData = {
            model: model,
            messages: messages,
            temperature: 0.7,
            stream: features.value.streamOutput,
            top_p: 1.0,
            instructions: financeSystemPrompt.value,
            enable_thinking: features.value.deepThink,
            tools: tools.length > 0 ? tools : undefined,
            tool_choice: tools.length > 0 ? "auto" : null,
            conversation: `finance_${financeActiveChatId.value}`,
            user_id: user_id
        };
        
        const response = await fetch('http://localhost:8888/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify(requestData),
            signal: abortController.value.signal
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'API请求失败');
        }
        
        if (features.value.streamOutput) {
            await handleFinanceStreamResponse(response);
        } else {
            await handleFinanceNormalResponse(response);
        }
        
        await refreshFinanceChatTitle();
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('发送金融助手消息错误:', error);
            financeMessages.value.push({
                role: 'assistant',
                content: '抱歉，发送消息时出现错误，请稍后重试。'
            });
        }
    } finally {
        isLoading.value = false;
        abortController.value = null;
    }
};

const handleFinanceStreamResponse = async (response) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let content = '';
    let outputParts = [];
    let buffer = '';
    let currentType = null;
    let lastDataReceivedTime = Date.now();
    let shouldShowLoading = false;
    let loadingTimer = null;
    let isLoading = true;
    
    const messageIndex = financeMessages.value.length - 1;
    
    const scheduleLoadingCheck = () => {
        if (loadingTimer) {
            clearTimeout(loadingTimer);
            loadingTimer = null;
        }
        loadingTimer = setTimeout(() => {
            if (isLoading) {
                shouldShowLoading = true;
                financeMessages.value[messageIndex].showLoading = true;
            }
        }, 1000);
    };
    
    scheduleLoadingCheck();
    
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (!line.trim().startsWith('data: ')) continue;
                
                const jsonStr = line.trim().slice(6);
                if (jsonStr === '[DONE]') continue;
                
                try {
                    const chunk = JSON.parse(jsonStr);
                    console.log('金融助手收到chunk:', chunk);
                    
                    lastDataReceivedTime = Date.now();
                    shouldShowLoading = false;
                    financeMessages.value[messageIndex].showLoading = false;
                    scheduleLoadingCheck();
                    
                    if (chunk.choices?.[0]?.delta?.function_call_request) {
                        console.log('金融助手收到函数调用请求:', chunk.choices[0].delta.function_call_request);
                        financeMessages.value[messageIndex].functionCallRequest = chunk.choices[0].delta.function_call_request;
                    }
                    
                    if (chunk.choices?.[0]?.delta?.content) {
                        content += chunk.choices[0].delta.content;
                        financeMessages.value[messageIndex].content = content;
                        currentType = null;
                        console.log('金融助手更新内容:', content);
                    }
                    
                    if (chunk.choices?.[0]?.delta?.reasoning_summary_text?.delta) {
                        console.log('金融助手收到深度思考数据:', chunk.choices[0].delta.reasoning_summary_text);
                        const reasoningData = chunk.choices[0].delta.reasoning_summary_text;
                        const summaryIndex = reasoningData.summary_index || 0;
                        
                        if (currentType !== 'reasoning') {
                            currentType = 'reasoning';
                            outputParts.push({
                                type: 'reasoning',
                                summaryIndex: summaryIndex,
                                content: reasoningData.delta || ''
                            });
                        } else {
                            const lastReasoningIndex = outputParts.length - 1;
                            if (lastReasoningIndex >= 0 && outputParts[lastReasoningIndex].type === 'reasoning') {
                                outputParts[lastReasoningIndex].content += reasoningData.delta || '';
                            } else {
                                outputParts.push({
                                    type: 'reasoning',
                                    summaryIndex: summaryIndex,
                                    content: reasoningData.delta || ''
                                });
                            }
                        }
                        
                        financeMessages.value[messageIndex].details.reasoning = outputParts
                            .filter(p => p.type === 'reasoning')
                            .map(p => p.content)
                            .join('');
                        financeMessages.value[messageIndex].outputParts = [...outputParts];
                        console.log('金融助手累计深度思考内容:', financeMessages.value[messageIndex].details.reasoning);
                    }
                    
                    if (chunk.choices?.[0]?.delta?.web_search_sources) {
                        console.log('金融助手收到搜索来源数据:', chunk.choices[0].delta.web_search_sources);
                        const sources = chunk.choices[0].delta.web_search_sources;
                        
                        let lastSearchIndex = outputParts.length - 1;
                        if (lastSearchIndex < 0 || outputParts[lastSearchIndex].type !== 'search') {
                            outputParts.push({
                                type: 'search',
                                sources: sources,
                                status: 'completed'
                            });
                        } else {
                            outputParts[lastSearchIndex].sources = [...outputParts[lastSearchIndex].sources, ...sources];
                        }
                        
                        financeMessages.value[messageIndex].details.sources = outputParts
                            .filter(p => p.type === 'search')
                            .flatMap(p => p.sources);
                        financeMessages.value[messageIndex].outputParts = [...outputParts];
                    }
                } catch (e) {
                    console.error('金融助手解析chunk错误:', e);
                }
            }
        }
    } finally {
        if (loadingTimer) {
            clearTimeout(loadingTimer);
        }
        financeMessages.value[messageIndex].showLoading = false;
        financeMessages.value[messageIndex].isStreaming = false;
    }
};

const handleFinanceNormalResponse = async (response) => {
    const data = await response.json();
    const messageIndex = financeMessages.value.length - 1;
    
    let content = '';
    let reasoning = '';
    let sources = [];
    let outputParts = [];
    
    if (data.output && Array.isArray(data.output)) {
        for (const item of data.output) {
            if (item.type === 'reasoning' && item.summary) {
                reasoning = item.summary.map(s => s.text).join('');
                outputParts.push({
                    type: 'reasoning',
                    content: reasoning
                });
            } else if (item.type === 'search' && item.sources) {
                sources = item.sources;
                outputParts.push({
                    type: 'search',
                    sources: sources,
                    status: 'completed'
                });
            } else if (item.type === 'message' && item.content) {
                content = item.content.map(c => c.text).join('');
            }
        }
    } else if (data.choices && data.choices[0]?.message?.content) {
        content = data.choices[0].message.content;
    }
    
    financeMessages.value[messageIndex].content = content;
    financeMessages.value[messageIndex].details = {
        reasoning: reasoning,
        sources: sources
    };
    financeMessages.value[messageIndex].outputParts = outputParts;
    financeMessages.value[messageIndex].isStreaming = false;
};

const refreshFinanceChatTitle = async () => {
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : userId.value;
        const response = await fetch(`http://localhost:8888/api/chats?user_id=${encodeURIComponent(user_id)}&type=2`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        if (response.ok) {
            const data = await response.json();
            data.chats.forEach(chat => {
                const existingChat = financeChatHistory.value.find(c => c.id === chat.id);
                if (existingChat) {
                    existingChat.title = chat.title;
                }
            });
        }
    } catch (error) {
        console.error('刷新金融助手对话标题失败:', error);
    }
};

const handleStreamResponse = async (response) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let content = '';
    let outputParts = [];
    let buffer = '';
    let currentType = null;
    let lastDataReceivedTime = Date.now();
    let shouldShowLoading = false;
    let loadingTimer = null;
    let isLoading = true;
    
    const messageIndex = currentMessages.value.length - 1;
    
    const scheduleLoadingCheck = () => {
        if (loadingTimer) {
            clearTimeout(loadingTimer);
            loadingTimer = null;
        }
        loadingTimer = setTimeout(() => {
            if (isLoading) {
                shouldShowLoading = true;
                currentMessages.value[messageIndex].showLoading = true;
            }
        }, 1000);
    };
    
    scheduleLoadingCheck();
    
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (!line.trim().startsWith('data: ')) continue;
                
                const jsonStr = line.trim().slice(6);
                if (jsonStr === '[DONE]') continue;
                
                try {
                    const chunk = JSON.parse(jsonStr);
                    console.log('收到chunk:', chunk);
                    
                    lastDataReceivedTime = Date.now();
                    shouldShowLoading = false;
                    currentMessages.value[messageIndex].showLoading = false;
                    scheduleLoadingCheck();
                    
                    if (chunk.choices?.[0]?.delta?.function_call_request) {
                        console.log('收到函数调用请求:', chunk.choices[0].delta.function_call_request);
                        currentMessages.value[messageIndex].functionCallRequest = chunk.choices[0].delta.function_call_request;
                    }
                    
                    if (chunk.choices?.[0]?.delta?.content) {
                        content += chunk.choices[0].delta.content;
                        currentMessages.value[messageIndex].content = content;
                        currentType = null;
                        console.log('更新内容:', content);
                    }
                    
                    if (chunk.choices?.[0]?.delta?.reasoning_summary_text?.delta) {
                        console.log('收到深度思考数据:', chunk.choices[0].delta.reasoning_summary_text);
                        const reasoningData = chunk.choices[0].delta.reasoning_summary_text;
                        const summaryIndex = reasoningData.summary_index || 0;
                        
                        if (currentType !== 'reasoning') {
                            currentType = 'reasoning';
                            outputParts.push({
                                type: 'reasoning',
                                summaryIndex: summaryIndex,
                                content: reasoningData.delta || ''
                            });
                        } else {
                            const lastReasoningIndex = outputParts.length - 1;
                            if (lastReasoningIndex >= 0 && outputParts[lastReasoningIndex].type === 'reasoning') {
                                outputParts[lastReasoningIndex].content += reasoningData.delta || '';
                            } else {
                                outputParts.push({
                                    type: 'reasoning',
                                    summaryIndex: summaryIndex,
                                    content: reasoningData.delta || ''
                                });
                            }
                        }
                        
                        currentMessages.value[messageIndex].details.reasoning = outputParts
                            .filter(p => p.type === 'reasoning')
                            .map(p => p.content)
                            .join('');
                        currentMessages.value[messageIndex].outputParts = [...outputParts];
                        console.log('累计深度思考内容:', currentMessages.value[messageIndex].details.reasoning);
                    }
                    
                    if (chunk.choices?.[0]?.delta?.web_search_sources) {
                        console.log('收到搜索来源数据:', chunk.choices[0].delta.web_search_sources);
                        const sources = chunk.choices[0].delta.web_search_sources;
                        
                        let lastSearchIndex = outputParts.length - 1;
                        if (lastSearchIndex < 0 || outputParts[lastSearchIndex].type !== 'search') {
                            currentType = 'search';
                            outputParts.push({
                                type: 'search',
                                sources: []
                            });
                            lastSearchIndex = outputParts.length - 1;
                        }
                        
                        if (lastSearchIndex >= 0 && outputParts[lastSearchIndex].type === 'search') {
                            sources.forEach(source => {
                                if (source.url) {
                                    outputParts[lastSearchIndex].sources.push({
                                        url: source.url,
                                        title: source.title || ''
                                    });
                                }
                            });
                        }
                        
                        currentMessages.value[messageIndex].details.sources = outputParts
                            .filter(p => p.type === 'search')
                            .flatMap(p => p.sources);
                        currentMessages.value[messageIndex].outputParts = [...outputParts];
                        console.log('累计搜索来源:', currentMessages.value[messageIndex].details.sources);
                    }
                } catch (err) {
                    console.warn('解析chunk失败:', jsonStr);
                }
            }
        }
        
        if (buffer.trim().startsWith('data: ')) {
            const jsonStr = buffer.trim().slice(6);
            if (jsonStr !== '[DONE]') {
                try {
                    const chunk = JSON.parse(jsonStr);
                    
                    if (chunk.choices?.[0]?.delta?.content) {
                        content += chunk.choices[0].delta.content;
                        currentMessages.value[messageIndex].content = content;
                    }
                } catch (err) {
                    console.warn('解析最终chunk失败:', jsonStr);
                }
            }
        }
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('流式响应处理错误:', error);
        } else {
            // 用户暂停，保存已输出的内容
            console.log('用户暂停，保存已输出的内容');
            await saveChatMessages();
            await refreshChatTitle();
        }
    } finally {
        isLoading = false;
        shouldShowLoading = false;
        currentMessages.value[messageIndex].showLoading = false;
        currentMessages.value[messageIndex].isStreaming = false;
        if (loadingTimer) {
            clearTimeout(loadingTimer);
            loadingTimer = null;
        }
    }
};

const handleNormalResponse = async (response) => {
    const data = await response.json();
    
    let content = '';
    let reasoning = '';
    let sources = [];
    
    if (data.output && Array.isArray(data.output)) {
        for (const item of data.output) {
            if (item.type === 'reasoning' && item.summary) {
                reasoning = item.summary.map(s => s.text).join('');
            } else if (item.type === 'search' && item.sources) {
                sources = item.sources;
            } else if (item.type === 'message' && item.content) {
                content = item.content.map(c => c.text).join('');
            }
        }
    }
    
    // 移除之前的 loading 消息
    if (currentMessages.value.length > 0 && currentMessages.value[currentMessages.value.length - 1].role === 'assistant' && !currentMessages.value[currentMessages.value.length - 1].content) {
        currentMessages.value.pop();
    }
    
    const assistantMessage = {
        role: 'assistant',
        content: content,
        details: {
            reasoning: reasoning,
            sources: sources
        },
        detailsExpanded: true
    };
    
    currentMessages.value.push(assistantMessage);
};

onMounted(async () => {
    initUserId();
    await loadModels();
    await loadSystemPrompt();
    const loaded = await loadChatHistory();
    if (!loaded || chatHistory.value.length === 0) {
        await createNewChat();
    } else {
        if (chatHistory.value.length > 0) {
            await switchChat(chatHistory.value[0].id);
        }
    }
});
</script>