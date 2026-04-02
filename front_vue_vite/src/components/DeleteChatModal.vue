<template>
    <div class="modal" @click.self="$emit('close')">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">确认删除</h3>
                <button class="close-btn" @click="$emit('close')" title="关闭">×</button>
            </div>
            <p>确定要删除这个对话吗？此操作无法撤销。</p>
            <label class="dont-ask-again">
                <input type="checkbox" v-model="dontAskAgain" id="dontAskAgain" name="dontAskAgain" />
                <span>不再提示</span>
            </label>
            <div class="modal-buttons">
                <button class="cancel-btn" @click="$emit('close')">取消</button>
                <button class="save-btn" @click="handleConfirm">确认删除</button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['close', 'confirm', 'dont-ask-again']);
const dontAskAgain = ref(false);

const handleConfirm = () => {
    emit('confirm');
    emit('dont-ask-again', dontAskAgain.value);
};
</script>

<style scoped>
p {
    color: #f8fafc;
    margin-bottom: 20px;
    line-height: 1.6;
}

.dont-ask-again {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
    cursor: pointer;
}

.dont-ask-again input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
}

.dont-ask-again span {
    color: #94a3b8;
    font-size: 14px;
}
</style>