<script setup lang="ts">
import { ref } from 'vue'
import { User, X, Save, Plus } from 'lucide-vue-next'
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
    <div class="modal-overlay" @click.self="emit('close')">
      <div class="modal-panel w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
        <div class="flex items-center gap-3 mb-5 -mt-1">
          <div class="w-10 h-10 rounded-full bg-chop-soft flex items-center justify-center border border-chop-border">
            <User :size="18" class="text-chop-light" />
          </div>
          <div class="flex-1">
            <h2 class="text-lg font-display font-semibold text-parchment">{{ t('chars.edit_title') }}</h2>
            <p class="text-xs text-muted mt-0.5">Refine character details and profile</p>
          </div>
          <button @click="emit('close')" class="btn btn-ghost p-2">
            <X :size="16" />
          </button>
        </div>

        <div class="divider !my-4" />

        <div class="space-y-4 stagger-children">
          <div>
            <label class="field-label">{{ t('chars.name') }}</label>
            <input
              v-model="formName"
              type="text"
              class="input"
            />
          </div>

          <div>
            <label class="field-label">{{ t('chars.role') }}</label>
            <select
              v-model="formRole"
              class="input"
            >
              <option value="protagonist">Protagonist</option>
              <option value="antagonist">Antagonist</option>
              <option value="supporting">Supporting</option>
              <option value="minor">Minor</option>
            </select>
          </div>

          <div>
            <label class="field-label">Appearance</label>
            <textarea
              v-model="formAppearance"
              rows="2"
              class="input resize-none"
            />
          </div>

          <div>
            <label class="field-label">Core Desire</label>
            <input
              v-model="formCoreDesire"
              type="text"
              class="input"
            />
          </div>

          <div>
            <label class="field-label">Deep Fear</label>
            <input
              v-model="formDeepFear"
              type="text"
              class="input"
            />
          </div>

          <div>
            <label class="field-label">Voice Sample</label>
            <textarea
              v-model="formVoiceSample"
              rows="2"
              class="input resize-none"
            />
          </div>

          <div>
            <label class="field-label">Arc Stage</label>
            <select
              v-model="formArcStage"
              class="input"
            >
              <option value="introduction">Introduction</option>
              <option value="rising_action">Rising Action</option>
              <option value="climax">Climax</option>
              <option value="resolution">Resolution</option>
            </select>
          </div>

          <div>
            <label class="field-label">Core Traits</label>
            <div class="flex flex-wrap gap-1.5 mb-2.5">
              <span
                v-for="(trait, idx) in formCoreTraits"
                :key="idx"
                class="badge badge-accent gap-1 pr-1"
              >
                {{ trait }}
                <button @click="removeTrait(idx)" class="btn btn-ghost !p-0 !w-4 !h-4 hover:bg-chop/20 rounded-full ml-0.5">
                  <X :size="10" />
                </button>
              </span>
            </div>
            <div class="flex gap-2">
              <input
                v-model="traitInput"
                type="text"
                placeholder="Add trait..."
                class="input flex-1 !py-1.5"
                @keydown.enter.prevent="addTrait"
              />
              <button @click="addTrait" class="btn btn-secondary btn-sm">
                <Plus :size="12" />
                Add
              </button>
            </div>
          </div>

          <div>
            <label class="field-label">Secrets</label>
            <div class="flex flex-wrap gap-1.5 mb-2.5">
              <span
                v-for="(secret, idx) in formSecrets"
                :key="idx"
                class="badge badge-gold gap-1 pr-1"
              >
                {{ secret }}
                <button @click="removeSecret(idx)" class="btn btn-ghost !p-0 !w-4 !h-4 hover:bg-gold/20 rounded-full ml-0.5">
                  <X :size="10" />
                </button>
              </span>
            </div>
            <div class="flex gap-2">
              <input
                v-model="secretInput"
                type="text"
                placeholder="Add secret..."
                class="input flex-1 !py-1.5"
                @keydown.enter.prevent="addSecret"
              />
              <button @click="addSecret" class="btn btn-secondary btn-sm">
                <Plus :size="12" />
                Add
              </button>
            </div>
          </div>

          <div>
            <label class="field-label">Knowledge Scope</label>
            <div class="flex flex-wrap gap-1.5 mb-2.5">
              <span
                v-for="(k, idx) in formKnowledgeScope"
                :key="idx"
                class="badge badge-editor gap-1 pr-1"
              >
                {{ k }}
                <button @click="removeKnowledge(idx)" class="btn btn-ghost !p-0 !w-4 !h-4 hover:bg-editor/20 rounded-full ml-0.5">
                  <X :size="10" />
                </button>
              </span>
            </div>
            <div class="flex gap-2">
              <input
                v-model="knowledgeInput"
                type="text"
                placeholder="Add knowledge area..."
                class="input flex-1 !py-1.5"
                @keydown.enter.prevent="addKnowledge"
              />
              <button @click="addKnowledge" class="btn btn-secondary btn-sm">
                <Plus :size="12" />
                Add
              </button>
            </div>
          </div>
        </div>

        <div class="divider !my-5" />

        <div class="flex justify-end gap-2">
          <button
            @click="emit('close')"
            class="btn btn-secondary"
          >
            {{ t('general.cancel') }}
          </button>
          <button
            @click="save"
            :disabled="!formName"
            class="btn btn-primary"
          >
            <Save :size="14" />
            {{ t('general.save') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
