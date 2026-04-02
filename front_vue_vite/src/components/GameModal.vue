<template>
    <div class="modal" @click.self="$emit('close')">
        <div class="modal-content" style="max-width: 400px;">
            <div class="modal-header">
                <h2 class="modal-title">选择智能体</h2>
                <button class="close-btn" @click="$emit('close')" title="关闭">×</button>
            </div>
            <div class="games-container">
                <div class="game-item" @click="selectGame('riddle')">
                    <div class="game-icon">🐢</div>
                    <div class="game-info">
                        <h3>海龟汤</h3>
                        <p>推理游戏，通过提问找出真相</p>
                    </div>
                </div>
                <div class="game-item" @click="selectGame('finance')">
                    <div class="game-icon">💰</div>
                    <div class="game-info">
                        <h3>金融助手</h3>
                        <p>智能金融分析与投资建议</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
const emit = defineEmits(['close', 'select-game']);

const selectGame = (gameType) => {
    emit('select-game', gameType);
    emit('close');
};
</script>

<style scoped>
.games-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.game-item {
    display: flex;
    align-items: center;
    padding: 15px;
    background-color: #334155;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.game-item:hover {
    background-color: #475569;
}

.game-icon {
    font-size: 40px;
    margin-right: 15px;
}

.game-info h3 {
    margin: 0 0 5px 0;
    font-size: 16px;
    color: #f8fafc;
}

.game-info p {
    margin: 0;
    font-size: 12px;
    color: #94a3b8;
}
</style>