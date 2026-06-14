import { ref, watch } from 'vue'

const STORAGE_KEY = 'm-movie-edit-mode'

const editMode = ref(sessionStorage.getItem(STORAGE_KEY) === 'true')

watch(editMode, (value) => {
  sessionStorage.setItem(STORAGE_KEY, value ? 'true' : 'false')
})

export const useEditMode = () => {
  const toggleEditMode = (): void => {
    editMode.value = !editMode.value
  }

  return { editMode, toggleEditMode }
}
