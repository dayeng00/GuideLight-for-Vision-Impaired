import component from 'element-plus/es/components/tree-select/src/tree-select-option.mjs'
import { createRouter, createWebHistory } from 'vue-router'

// 导入组件（推荐使用懒加载）
const Home = () => import('../views/Home.vue')
const About = () => import('../views/About.vue')
const Login = () => import('../views/Login.vue')
const Register = () => import('../views/Register.vue')
const Scan = () => import('../views/Scan.vue')
const Record = () => import('../views/Record.vue')
const Demonstrate = () => import('../views/Demonstrate.vue')

// scan 子组件
const base_Video = () => import('../views/show/base_Video.vue')
const feature_detector = () => import('../views/show/feature_detector.vue')
const feature_tracker = () => import('../views/show/feature_track.vue')
const disparity_estimator = () => import('../views/show/disparity_estimator.vue')
const gesture_recognizer = () => import('../views/show/gesture_recognizer.vue')
const gesture_point_recognition = () => import('../views/show/gesture_point_recognition.vue')
const moblie_net_SSD_detector = () => import('../views/show/moblie_net_SSD_detector.vue')
const person_detection_tracker_on_video = () => import('../views/show/person_detection_tracker_on_video.vue')
const spatial_object_tracker_on_RGB = () => import('../views/show/spatial_object_tracker_on_RGB.vue')

const routes = [
  {
    path: '/home',
    name: 'Home',
    component: Home
  },
  {
    path: '/about',
    name: 'About',
    component: About
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'default',
    component: Home
  },
  {
    path: '/register',
    name: 'Register',
    component: Register
  },
  {
    path: '/scan',
    name: 'Scan',
    component: Scan,  
    children: [
      {
        path: '',
        component: base_Video
      },
      {
        path: 'base_video',
        component: base_Video
      }
      ,
      {
        path: 'feature_detector',
        component: feature_detector
      },
      {
        path: 'feature_tracker',
        component: feature_tracker
      },
      {
        path: 'disparity_estimator',
        component: disparity_estimator
      },
      {
        path: 'gesture_recognizer',
        component: gesture_recognizer
      },
      {
        path: 'gesture_point_recognition',
        component: gesture_point_recognition
      },
      {
        path: 'moblie_net_SSD_detector',
        component: moblie_net_SSD_detector
      },
      {
        path: 'person_detection_tracker_on_video',
        component: person_detection_tracker_on_video
      },
      {
        path: 'spatial_object_tracker_on_RGB',
        component: spatial_object_tracker_on_RGB
      }
    ]
  },
  {
    path: '/record',
    name: 'Record',
    component: Record
  },
  {
    path: '/demonstrate',
    name: 'Demonstrate',
    component: Demonstrate  
  },
  
]

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes
  })
export default router