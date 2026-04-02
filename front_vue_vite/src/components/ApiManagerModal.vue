<template>
    <div class="modal" @click.self="$emit('close')">
        <div class="modal-content api-manager-content">
            <div class="modal-header">
                <h3 class="modal-title">API管理</h3>
                <button class="close-btn" @click="$emit('close')" title="关闭">×</button>
            </div>
            
            <div class="api-container">
                <!-- 左侧：已有API配置 -->
                <div class="api-section">
                    <h3>已有API配置</h3>
                    <div class="api-list-container">
                        <div v-if="apiConfigs.length === 0" class="api-empty">
                            暂无API配置
                        </div>
                        <div v-else class="api-list-items">
                            <div v-for="config in apiConfigs" :key="config.id" class="api-list-item">
                                <div class="api-list-item-header">
                                    <span class="api-list-item-name">{{ config.name }}</span>
                                    <div class="api-list-item-badges">
                                        <span v-if="config.isDefault" class="api-list-item-default">默认</span>
                                        <span v-if="config.isFinanceDefault" class="api-list-item-finance">金融</span>
                                        <span v-if="!config.isGlobal" class="api-list-item-personal">个人</span>
                                        <span v-else class="api-list-item-global">全局</span>
                                    </div>
                                </div>
                                <div class="api-list-item-details">
                                    <div>URL: {{ maskUrl(config.apiUrl) }}</div>
                                </div>
                                <div class="api-list-item-actions">
                                    <button v-if="!config.isGlobal" class="btn-update" @click="handleUpdateApi(config)">更新</button>
                                    <button v-if="!config.isGlobal" class="btn-delete" @click="handleDeleteApi(config.id)">删除</button>
                                    <button v-if="!config.isDefault" class="btn-set-default" @click="handleSetDefault(config.id)">设为默认</button>
                                    <button v-if="!config.isFinanceDefault" class="btn-set-finance" @click="handleSetFinanceDefault(config.id)">设为金融默认</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 右侧：添加新API -->
                <div class="api-section">
                    <h3>添加新API</h3>
                    <div class="api-form">
                        <div class="form-item">
                            <label for="apiName">模型名称</label>
                            <input v-model="newApi.name" type="text" placeholder="例如：qwen3.5-plus" id="apiName" name="apiName" />
                        </div>
                        <div class="form-item">
                            <label for="apiKey">API Key</label>
                            <input v-model="newApi.apiKey" type="password" placeholder="输入API Key" id="apiKey" name="apiKey" />
                        </div>
                        <div class="form-item">
                            <label for="apiUrl">API URL</label>
                            <input v-model="newApi.apiUrl" type="text" placeholder="输入API URL" id="apiUrl" name="apiUrl" />
                        </div>
                    </div>
                </div>
            </div>

            <div class="modal-buttons">
                <button class="cancel-btn" @click="$emit('close')">取消</button>
                <button class="save-btn" @click="handleAddApi">保存</button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const props = defineProps({
    userId: {
        type: String,
        default: ''
    }
});

const emit = defineEmits(['close', 'refresh-models']);

const apiConfigs = ref([]);
const newApi = ref({
    name: '',
    apiKey: '',
    apiUrl: ''
});

const loadApiConfigs = async () => {
    try {
        const response = await fetch(`http://localhost:8888/api/model-configs?user_id=${encodeURIComponent(props.userId)}`, {
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });
        if (response.ok) {
            const data = await response.json();
            apiConfigs.value = data.models || [];
        }
    } catch (error) {
        console.error('加载API配置失败:', error);
    }
};

const maskUrl = (url) => {
    if (!url) return '';
    if (url.length <= 20) return url;
    return url.substring(0, 20) + '...';
};

const handleAddApi = async () => {
    if (!newApi.value.name || !newApi.value.apiKey || !newApi.value.apiUrl) {
        alert('请填写完整的API配置信息');
        return;
    }

    try {
        const response = await fetch('http://localhost:8888/api/model-configs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                name: newApi.value.name,
                apiKey: newApi.value.apiKey,
                apiUrl: newApi.value.apiUrl,
                userId: props.userId
            })
        });

        if (response.ok) {
            alert('API配置保存成功');
            newApi.value = { name: '', apiKey: '', apiUrl: '' };
            await loadApiConfigs();
            emit('refresh-models');
        } else {
            const error = await response.json();
            alert('保存失败: ' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('保存API配置失败:', error);
        alert('保存失败: ' + error.message);
    }
};

const handleDeleteApi = async (configId) => {
    if (!confirm('确定要删除这个API配置吗？')) {
        return;
    }

    try {
        const response = await fetch(`http://localhost:8888/api/model-configs/${configId}?user_id=${encodeURIComponent(props.userId)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });

        if (response.ok) {
            alert('API配置删除成功');
            await loadApiConfigs();
            emit('refresh-models');
        } else {
            const error = await response.json();
            alert('删除失败: ' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('删除API配置失败:', error);
        alert('删除失败: ' + error.message);
    }
};

const handleSetDefault = async (configId) => {
    try {
        const response = await fetch(`http://localhost:8888/api/model-configs/${configId}/default?user_id=${encodeURIComponent(props.userId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            }
        });

        if (response.ok) {
            alert('默认API设置成功');
            await loadApiConfigs();
            emit('refresh-models');
        } else {
            const error = await response.json();
            alert('设置失败: ' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('设置默认API失败:', error);
        alert('设置失败: ' + error.message);
    }
};

const handleSetFinanceDefault = async (configId) => {
    try {
        const response = await fetch(`http://localhost:8888/api/finance-config/default-model?user_id=${encodeURIComponent(props.userId)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                model_id: configId
            })
        });

        if (response.ok) {
            alert('金融助手默认模型设置成功');
            await loadApiConfigs();
            emit('refresh-models');
        } else {
            const error = await response.json();
            alert('设置失败: ' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('设置金融助手默认模型失败:', error);
        alert('设置失败: ' + error.message);
    }
};

const handleUpdateApi = async (config) => {
    const newName = prompt('请输入新的模型名称:', config.name);
    if (newName === null) return;

    const newApiKey = prompt('请输入新的API Key:');
    if (newApiKey === null) return;

    const newApiUrl = prompt('请输入新的API URL:');
    if (newApiUrl === null) return;

    if (!newName || !newApiKey || !newApiUrl) {
        alert('请填写完整的API配置信息');
        return;
    }

    try {
        const response = await fetch(`http://localhost:8888/api/model-configs/${config.id}?user_id=${encodeURIComponent(props.userId)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                name: newName,
                apiKey: newApiKey,
                apiUrl: newApiUrl
            })
        });

        if (response.ok) {
            alert('API配置更新成功');
            await loadApiConfigs();
            emit('refresh-models');
        } else {
            const error = await response.json();
            alert('更新失败: ' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('更新API配置失败:', error);
        alert('更新失败: ' + error.message);
    }
};

onMounted(() => {
    loadApiConfigs();
});
</script>

<style scoped>
.api-manager-content {
    max-width: 800px;
    max-height: 80vh;
    overflow-y: auto;
}

.api-container {
    display: flex;
    gap: 20px;
    margin-bottom: 10px;
}

.api-section {
    flex: 1;
    padding: 15px;
    background-color: #334155;
    border-radius: 8px;
}

.api-section h3 {
    margin-bottom: 15px;
    color: #38bdf8;
    font-size: 16px;
}

.api-list-container {
    max-height: 200px;
    overflow-y: auto;
}

.api-empty {
    color: #94a3b8;
    text-align: center;
    padding: 15px;
}

.api-list-items {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.api-list-item {
    background-color: #475569;
    border: 1px solid #64748b;
    border-radius: 6px;
    padding: 10px;
}

.api-list-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.api-list-item-name {
    font-weight: bold;
    color: #38bdf8;
    font-size: 14px;
}

.api-list-item-badges {
    display: flex;
    gap: 4px;
}

.api-list-item-default {
    background-color: #10b981;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
}

.api-list-item-personal {
    background-color: #10b981;
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
}

.api-list-item-global {
    background-color: #8b5cf6;
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
}

.api-list-item-details {
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 8px;
}

.api-list-item-actions {
    display: flex;
    gap: 8px;
}

.api-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.form-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.form-item label {
    color: #94a3b8;
    font-size: 13px;
}

.form-item input {
    padding: 6px 8px;
    background-color: #475569;
    border: 1px solid #64748b;
    border-radius: 4px;
    color: #f8fafc;
    font-size: 13px;
}

.btn-update,
.btn-delete,
.btn-set-default,
.btn-set-finance {
    padding: 4px 12px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.3s ease;
}

.btn-update {
    background-color: #38bdf8;
    color: #0f172a;
}

.btn-update:hover {
    background-color: #0ea5e9;
}

.btn-delete {
    background-color: #ef4444;
    color: white;
}

.btn-delete:hover {
    background-color: #dc2626;
}

.btn-set-default {
    background-color: #38bdf8;
    color: #0f172a;
}

.btn-set-default:hover {
    background-color: #0ea5e9;
}

.btn-set-finance {
    background-color: #f59e0b;
    color: #0f172a;
}

.btn-set-finance:hover {
    background-color: #d97706;
}

.api-list-item-finance {
    background-color: #f59e0b;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
}

.modal-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 0px;
}

.cancel-btn {
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    padding: 10px 20px;
    border-radius: 6px;
    cursor: pointer;
}

.save-btn {
    background-color: #38bdf8;
    color: #0f172a;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
}
</style>
