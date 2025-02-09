import { defineStore } from "pinia";

export const useUserStore = defineStore("user", {
  state: () => ({
    user: null, // 存储当前登录用户信息
  }),
  
  actions: {
    // 设置用户数据
    setUser(userData) {
      this.user = userData;

      // 将用户信息存入 LocalStorage，防止刷新丢失
      localStorage.setItem("user", JSON.stringify(this.user));
    },

    // 从 LocalStorage 加载用户信息，防止刷新丢失
    loadUser() {
        const userData = localStorage.getItem('user');
        if (userData) {
          try {
            this.user = JSON.parse(userData);
            this.isLoggedIn = true;
          } catch (error) {
            this.clearUser();
          }
        }
      },

    // 退出登录
    logout() {
      this.user = null;
      localStorage.removeItem("user");
    }
  },

  getters: {
    // 获取用户 ID
    userId: (state) => state.user?.id || null,
    
    // 获取用户名
    userName: (state) => state.user?.name || "",

    // 获取用户分类
    userCategory: (state) => state.user?.category || "",

    // 获取操作时间
    userTime: (state) => state.user?.created_at || "",

    // 检查是否已登录
    isAuthenticated: (state) => !!state.user,
  },
});
