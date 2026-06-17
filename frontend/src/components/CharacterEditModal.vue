<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from '../i18n'
import type { CharacterProfile } from '../types/api'

const { t } = useI18n()

const props = defineProps<{
  character: CharacterProfile
}>()

const emit = defineEmits<{
  save: [data: Partial<CharacterProfile>]
  close: []
}>()

const formName = ref(props.character.name)
const formRole = ref(props.character.role)
const formAppearance = ref(props.character.appearance)
const formCoreDesire = ref(props.character.core_desire)
const formDeepFear = ref(props.character.deep_fear)
const formVoiceSample = ref(props.character.voice_sample)
const formArcStage = ref(props.character.arc_stage)
const formCoreTraits = ref<string[]>([...(props.character.personality?.core_traits || [])])
const formSecrets = ref<string[]>([...(props.character.secrets || [])])
const formKnowledgeScope = ref<string[]>([...(props.character.knowledge_scope || [])])
const traitInput = ref('')
const secretInput = ref('')
const knowledgeInput = ref('')

function addTrait(): void {
  const v = traitInput.value.trim()
  if (v && !formCoreTraits.value.includes(v)) {
    formCoreTraits.value.push(v)
  }
  traitInput.value = ''
}

function removeTrait(idx: number): void {
  formCoreTraits.value.splice(idx, 1)
}

function addSecret(): void {
  const v = secretInput.value.trim()
  if (v && !formSecrets.value.includes(v)) {
    formSecrets.value.push(v)
  }
  secretInput.value = ''
}

function removeSecret(idx: number): void {
  formSecrets.value.splice(idx, 1)
}

function addKnowledge(): void {
  const v = knowledgeInput.value.trim()
  if (v && !formKnowledgeScope.value.includes(v)) {
    formKnowledgeScope.value.push(v)
  }
  knowledgeInput.value = ''
}

function removeKnowledge(idx: number): void {
  formKnowledgeScope.value.splice(idx, 1)
}

function save(): void {
  emit('save', {
    name: formName.value,
    role: formRole.value,
    appearance: formAppearance.value,
    core_desire: formCoreDesire.value,
    deep_fear: formDeepFear.value,
    voice_sample: formVoiceSample.value,
    arc_stage: formArcStage.value,
    personality: {
      ...props.character.personality,
      core_traits: formCoreTraits.value,
    },
    secrets: formSecrets.value,
    knowledge_scope: formKnowledgeScope.value,
  })
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      @click.self="emit('close')"
    >
      <div class="bg-ink-panel border border-ink-edge rounded-xl p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
        <h2 class="text-lg font-semibold text-parchment mb-4">{{ t('chars.edit_title') }}</h2>
        <div class="space-y-4">
          <!-- Name -->
          <div>
            <label class="block text-xs text-muted mb-1">{{ t('chars.name') }}</label>
            <input
              v-model="formName"
              type="text"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
            />
          </div>

          <!-- Role -->
          <div>
            <label class="block text-xs text-muted mb-1">{{ t('chars.role') }}</label>
            <select
              v-model="formRole"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
            >
              <option value="protagonist">Protagonist</option>
              <option value="antagonist">Antagonist</option>
              <option value="supporting">Supporting</option>
              <option value="minor">Minor</option>
            </select>
          </div>

          <!-- Appearance -->
          <div>
            <label class="block text-xs text-muted mb-1">Appearance</label>
            <textarea
              v-model="formAppearance"
              rows="2"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop resize-none"
            />
          </div>

          <!-- Core Desire -->
          <div>
            <label class="block text-xs text-muted mb-1">Core Desire</label>
            <input
              v-model="formCoreDesire"
              type="text"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
            />
          </div>

          <!-- Deep Fear -->
          <div>
            <label class="block text-xs text-muted mb-1">Deep Fear</label>
            <input
              v-model="formDeepFear"
              type="text"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
            />
          </div>

          <!-- Voice Sample -->
          <div>
            <label class="block text-xs text-muted mb-1">Voice Sample</label>
            <textarea
              v-model="formVoiceSample"
              rows="2"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop resize-none"
            />
          </div>

          <!-- Arc Stage -->
          <div>
            <label class="block text-xs text-muted mb-1">Arc Stage</label>
            <select
              v-model="formArcStage"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
            >
              <option value="introduction">Introduction</option>
              <option value="rising_action">Rising Action</option>
              <option value="climax">Climax</option>
              <option value="resolution">Resolution</option>
            </select>
          </div>

          <!-- Core Traits -->
          <div>
            <label class="block text-xs text-muted mb-1">Core Traits</label>
            <div class="flex flex-wrap gap-1 mb-2">
              <span
                v-for="(trait, idx) in formCoreTraits"
                :key="idx"
                class="flex items-center gap-1 px-2 py-0.5 bg-chop/20/30 text-chop text-xs rounded-full"
              >
                {{ trait }}
                <button @click="removeTrait(idx)" class="hover:text-red-400">&times;</button>
              </span>
            </div>
            <div class="flex gap-2">
              <input
                v-model="traitInput"
                type="text"
                placeholder="Add trait..."
                class="flex-1 bg-ink-elevated border border-ink-edge rounded-lg px-3 py-1.5 text-sm text-parchment focus:outline-none focus:border-chop"
                @keydown.enter.prevent="addTrait"
              />
              <button @click="addTrait" class="px-3 py-1.5 bg-ink-elevated text-parchment-dim rounded-lg text-xs hover:bg-ink-elevated transition-colors">Add</button>
            </div>
          </div>

          <!-- Secrets -->
          <div>
            <label class="block text-xs text-muted mb-1">Secrets</label>
            <div class="flex flex-wrap gap-1 mb-2">
              <span
                v-for="(secret, idx) in formSecrets"
                :key="idx"
                class="flex items-center gap-1 px-2 py-0.5 bg-ink-elevated text-parchment-dim text-xs rounded-full"
              >
                {{ secret }}
                <button @click="removeSecret(idx)" class="hover:text-red-400">&times;</button>
              </span>
            </div>
            <div class="flex gap-2">
              <input
                v-model="secretInput"
                type="text"
                placeholder="Add secret..."
                class="flex-1 bg-ink-elevated border border-ink-edge rounded-lg px-3 py-1.5 text-sm text-parchment focus:outline-none focus:border-chop"
                @keydown.enter.prevent="addSecret"
              />
              <button @click="addSecret" class="px-3 py-1.5 bg-ink-elevated text-parchment-dim rounded-lg text-xs hover:bg-ink-elevated transition-colors">Add</button>
            </div>
          </div>

          <!-- Knowledge Scope -->
          <div>
            <label class="block text-xs text-muted mb-1">Knowledge Scope</label>
            <div class="flex flex-wrap gap-1 mb-2">
              <span
                v-for="(k, idx) in formKnowledgeScope"
                :key="idx"
                class="flex items-center gap-1 px-2 py-0.5 bg-ink-elevated text-parchment-dim text-xs rounded-full"
              >
                {{ k }}
                <button @click="removeKnowledge(idx)" class="hover:text-red-400">&times;</button>
              </span>
            </div>
            <div class="flex gap-2">
              <input
                v-model="knowledgeInput"
                type="text"
                placeholder="Add knowledge area..."
                class="flex-1 bg-ink-elevated border border-ink-edge rounded-lg px-3 py-1.5 text-sm text-parchment focus:outline-none focus:border-chop"
                @keydown.enter.prevent="addKnowledge"
              />
              <button @click="addKnowledge" class="px-3 py-1.5 bg-ink-elevated text-parchment-dim rounded-lg text-xs hover:bg-ink-elevated transition-colors">Add</button>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <button
            @click="emit('close')"
            class="px-4 py-2 text-sm text-parchment-dim hover:text-parchment transition-colors"
          >
            {{ t('general.cancel') }}
          </button>
          <button
            @click="save"
            :disabled="!formName"
            class="px-4 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 transition-colors"
          >
            {{ t('general.save') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
