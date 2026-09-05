<template>
  <div class="members">
    <div class="header">
      <h4>空间成员</h4>
      <el-button size="small" type="primary" @click="showAdd = true">添加成员</el-button>
    </div>

    <el-table :data="members" v-loading="loading" stripe>
      <el-table-column prop="user.nickname" label="昵称" />
      <el-table-column prop="user.email" label="邮箱" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <el-tag :type="roleTag(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="加入时间" width="180">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button
            v-if="row.role !== 'owner'"
            text
            type="danger"
            size="small"
            @click="remove(row.user.id)"
          >
            移除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAdd" title="添加成员" width="400px">
      <el-form label-position="top">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="输入用户注册邮箱" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option label="管理员" value="admin" />
            <el-option label="成员" value="member" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="add">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listMembers, addMember, removeMember, type SpaceMember } from '@/api/spaces'

const props = defineProps<{ spaceId: number }>()
const members = ref<SpaceMember[]>([])
const loading = ref(true)
const showAdd = ref(false)
const adding = ref(false)
const form = reactive({ email: '', role: 'member' })

onMounted(async () => {
  try {
    members.value = await listMembers(props.spaceId)
  } finally {
    loading.value = false
  }
})

async function add() {
  if (!form.email.trim()) {
    ElMessage.warning('请输入邮箱')
    return
  }
  adding.value = true
  try {
    await addMember(props.spaceId, form.email.trim(), form.role)
    showAdd.value = false
    form.email = ''
    form.role = 'member'
    members.value = await listMembers(props.spaceId)
    ElMessage.success('添加成功')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '添加失败')
  } finally {
    adding.value = false
  }
}

async function remove(userId: number) {
  try {
    await removeMember(props.spaceId, userId)
    members.value = members.value.filter((m) => m.user.id !== userId)
    ElMessage.success('已移除')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '移除失败')
  }
}

function roleLabel(r: string) {
  return { owner: '所有者', admin: '管理员', member: '成员' }[r] || r
}
function roleTag(r: string) {
  return r === 'owner' ? 'danger' : r === 'admin' ? 'warning' : 'info'
}
function fmt(d: string) {
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.members { padding: 16px 0; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header h4 { margin: 0; }
</style>