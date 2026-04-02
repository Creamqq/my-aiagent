<template>
    <div class="modal" @click.self="handleClose">
        <div class="modal-content kuaiqi-modal">
            <div class="modal-header">
                <h3 class="modal-title">快期账户配置</h3>
                <button class="close-btn" @click="handleClose" title="关闭">×</button>
            </div>
            <div class="modal-body">
                <div class="info-banner">
                    <svg class="info-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M12 16V12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M12 8H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span>配置快期账户信息后，大模型可以自动从快期获取实时行情数据~</span>
                </div>
                <div class="form-group">
                    <label for="kuaiqiAccount">快期账户</label>
                    <input 
                        type="text" 
                        id="kuaiqiAccount" 
                        name="kuaiqiAccount"
                        v-model="localAccount" 
                        placeholder="请输入快期账户"
                        autocomplete="off"
                    />
                </div>
                <div class="form-group">
                    <label for="kuaiqiPassword">账户密码</label>
                    <input 
                        type="password" 
                        id="kuaiqiPassword" 
                        name="kuaiqiPassword"
                        v-model="localPassword" 
                        placeholder="请输入账户密码"
                        autocomplete="new-password"
                    />
                </div>
                <div v-if="showSkip" class="skip-hint">
                    <span>您也可以稍后在设置中配置，当前可选择跳过。</span>
                </div>
            </div>
            <div class="modal-buttons">
                <button v-if="showSkip" class="skip-btn" @click="handleSkip">跳过</button>
                <button class="save-btn" @click="handleSave" :disabled="isSaving">
                    {{ isSaving ? '保存中...' : '保存配置' }}
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
    kuaiqiAccount: {
        type: String,
        default: ''
    },
    hasPassword: {
        type: Boolean,
        default: false
    },
    showSkip: {
        type: Boolean,
        default: true
    }
});

const emit = defineEmits(['close', 'save', 'skip']);

const localAccount = ref(props.kuaiqiAccount);
const localPassword = ref('');
const isSaving = ref(false);

watch(() => props.kuaiqiAccount, (newVal) => {
    localAccount.value = newVal;
});

const handleClose = () => {
    emit('close');
};

const handleSkip = () => {
    emit('skip');
    emit('close');
};

const handleSave = async () => {
    isSaving.value = true;
    try {
        emit('save', {
            account: localAccount.value,
            password: localPassword.value
        });
    } finally {
        isSaving.value = false;
    }
};
</script>

<style scoped>
.kuaiqi-modal {
    max-width: 480px;
}

.modal-body {
    padding: 16px 0;
}

.info-banner {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(99, 102, 241, 0.1) 100%);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 8px;
    margin-bottom: 20px;
    color: #93c5fd;
    font-size: 14px;
    line-height: 1.5;
}

.info-icon {
    flex-shrink: 0;
    color: #3b82f6;
    margin-top: 2px;
}

.form-group {
    margin-bottom: 16px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    color: #94a3b8;
    font-size: 14px;
    font-weight: 500;
}

.form-group input {
    width: 100%;
    padding: 12px 14px;
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid rgba(71, 85, 105, 0.5);
    border-radius: 8px;
    color: #e2e8f0;
    font-size: 14px;
    transition: all 0.2s ease;
}

.form-group input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.form-group input::placeholder {
    color: #64748b;
}

.skip-hint {
    text-align: center;
    color: #64748b;
    font-size: 13px;
    margin-top: 8px;
}

.modal-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding-top: 16px;
    border-top: 1px solid rgba(71, 85, 105, 0.3);
}

.skip-btn {
    padding: 10px 20px;
    background: transparent;
    border: 1px solid rgba(71, 85, 105, 0.5);
    border-radius: 8px;
    color: #94a3b8;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.skip-btn:hover {
    background: rgba(71, 85, 105, 0.2);
    border-color: rgba(71, 85, 105, 0.8);
    color: #e2e8f0;
}

.save-btn {
    padding: 10px 24px;
    background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
    border: none;
    border-radius: 8px;
    color: white;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
}

.save-btn:hover:not(:disabled) {
    background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.save-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
</style>
