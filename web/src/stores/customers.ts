import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import supabase from '@/api/supabase'

export interface Customer {
  id: string
  ref_key: string
  code: string | null
  description: string
  description_full: string | null
  inn: string | null
  kpp: string | null
  legal_entity_type: string | null
  phone_work: string | null
  phone_mobile: string | null
  email: string | null
  address_legal: string | null
  address_actual: string | null
  deletion_mark: boolean
  created_at: string
  updated_at: string
}

export const useCustomerStore = defineStore('customers', () => {
  const customers = ref<Customer[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const total = ref(0)

  const activeCustomers = computed(() => 
    customers.value.filter(c => !c.deletion_mark)
  )

  async function fetchCustomers(options: {
    page?: number
    pageSize?: number
    search?: string
    includeDeleted?: boolean
  } = {}) {
    loading.value = true
    error.value = null

    try {
      let query = supabase
        .from('customers')
        .select('*', { count: 'exact' })

      if (!options.includeDeleted) {
        query = query.eq('deletion_mark', false)
      }

      if (options.search) {
        query = query.or(`description.ilike.%${options.search}%,inn.ilike.%${options.search}%`)
      }

      const page = options.page || 1
      const pageSize = options.pageSize || 20
      const from = (page - 1) * pageSize
      const to = from + pageSize - 1

      query = query.range(from, to).order('updated_at', { ascending: false })

      const { data, error: supabaseError, count } = await query

      if (supabaseError) throw supabaseError

      customers.value = data || []
      total.value = count || 0
    } catch (e: any) {
      error.value = e.message
      console.error('Failed to fetch customers:', e)
    } finally {
      loading.value = false
    }
  }

  async function getCustomerById(id: string): Promise<Customer | null> {
    const { data, error: supabaseError } = await supabase
      .from('customers')
      .select('*')
      .eq('id', id)
      .single()

    if (supabaseError) {
      console.error('Failed to get customer:', supabaseError)
      return null
    }

    return data
  }

  async function updateCustomer(id: string, updates: Partial<Customer>): Promise<boolean> {
    const { error: supabaseError } = await supabase
      .from('customers')
      .update(updates)
      .eq('id', id)

    if (supabaseError) {
      console.error('Failed to update customer:', supabaseError)
      return false
    }

    // 更新本地状态
    const index = customers.value.findIndex(c => c.id === id)
    if (index !== -1) {
      customers.value[index] = { ...customers.value[index], ...updates }
    }

    return true
  }

  return {
    customers,
    activeCustomers,
    loading,
    error,
    total,
    fetchCustomers,
    getCustomerById,
    updateCustomer,
  }
})
