<template>
  <div class="page">
    <div class="header">
      <h3>知识空间</h3>
      <el-button type="primary" @click="dialogVisible = true">新建空间</el-button>
    </div>

    <el-row :gutter="16">
      <el-col v-for="space in spaces" :key="space.id" :span="8">
        <el-card class="space-card" shadow="hover">
          <div class="space-title">
            <span>{{ space.name }}</span>
            <el-tag size="small" :type="roleTagType(space.my_role)">
              {{ roleLabel(space.my_role) }}
            </el-tag>
          </div>
          <div class="space-desc">{{ space.description || '暂无描述' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && spaces.length === 0" description="还没有空间，点击右上角创建" />

    <el-dialog v-model="dialogVisible" title="新建知识空间" width="420px">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="form.name" maxlength="128" placeholder="如：产品研发部" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createSpace, listSpaces, type Space } from '@/api/spaces'

const spaces = ref<Space[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const creating = ref(false)
const form = reactive({ name: '', description: '' })

onMounted(async () => {
  try {
    spaces.value = await listSpaces()
  } finally {
    loading.value = false
  }
})

async function create() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入空间名称')
    return
  }
  creating.value = true
  try {
    const space = await createSpace(form.name.trim(), form.description.trim())
    spaces.value.unshift(space)
    dialogVisible.value = false
    form.name = ''
    form.description = ''
    ElMessage.success('创建成功')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } } }
    ElMessage.error(err.response?.data?.message ?? '创建失败')
  } finally {
    creating.value = false
  }
}

function roleLabel(role: string) {
  return { owner: '所有者', admin: '管理员', member: '成员' }[role] ?? role
}
function roleTagType(role: string): 'danger' | 'warning' | 'info' {
  return role === 'owner' ? 'danger' : role === 'admin' ? 'warning' : 'info'
}
</script>

<style scoped>
.page {
  padding: 24px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.space-card {
  margin-bottom: 16px;
  cursor: pointer;
}
.space-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.space-desc {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  min-height: 20px;
}
</style>
