declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// 解决Vue模板编译器的内部类型警告
declare global {
  const __VLS_intrinsicElements: any
  const __VLS_functionalComponentArgsRest: any
  const __VLS_NormalizeEmits: any
  const __VLS_pickFunctionalComponentCtx: any
  const __VLS_FunctionalComponentProps: any
  const __VLS_elementAsFunctionalComponent: any
  const __VLS_asFunctionalComponent: any
} 