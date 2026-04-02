<template>
    <div>
        <LoginForm v-if="currentView === 'login'" @login="handleLogin" @show-register="currentView = 'register'" />
        <RegisterForm v-else-if="currentView === 'register'" @register="handleRegister" @show-login="currentView = 'login'" />
        <MainApp v-else-if="currentView === 'app'" :user="currentUser" @logout="handleLogout" />
    </div>
</template>

<script setup>
import { ref } from 'vue';
import LoginForm from './components/LoginForm.vue';
import RegisterForm from './components/RegisterForm.vue';
import MainApp from './components/MainApp.vue';

const currentView = ref('login');
const currentUser = ref(null);

const checkLoginStatus = () => {
    const userData = localStorage.getItem('agent_user_data');
    if (userData) {
        try {
            currentUser.value = JSON.parse(userData);
            currentView.value = 'app';
        } catch (error) {
            console.error('解析用户数据失败:', error);
            currentView.value = 'login';
        }
    } else {
        currentView.value = 'login';
    }
};

const handleLogin = (user) => {
    console.log('App.handleLogin 接收到的用户数据:', user);
    currentUser.value = user;
    console.log('App.currentUser 已设置:', currentUser.value);
    currentView.value = 'app';
};

const handleRegister = (user) => {
    currentUser.value = user;
    currentView.value = 'app';
};

const handleLogout = () => {
    currentUser.value = null;
    currentView.value = 'login';
};

checkLoginStatus();
</script>