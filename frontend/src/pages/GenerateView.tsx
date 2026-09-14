import { useState } from 'react'
import type { SubmitEvent } from 'react'

// Local, string-based form state -- T018 converts this into a typed
// GenerateRequest and wires the actual submit/loading/result behavior.
interface FormState {
  location: string
  calendarLengthDays: string
  maxCost: string
  eventTypes: string
  genres: string
  startAfter: string
  startBefore: string
  model: string
}

const initialFormState: FormState = {
  location: '',
  calendarLengthDays: '',
  maxCost: '',
  eventTypes: '',
  genres: '',
  startAfter: '',
  startBefore: '',
  model: '',
}

export default function GenerateView() {
  const [form, setForm] = useState<FormState>(initialFormState)

  function updateField<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
  }

  return (
    <section>
      <h1>Generate a calendar</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="location">Location</label>
          <input
            id="location"
            type="text"
            required
            value={form.location}
            onChange={(e) => updateField('location', e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="calendar-length-days">Calendar length (days)</label>
          <input
            id="calendar-length-days"
            type="number"
            min={1}
            required
            value={form.calendarLengthDays}
            onChange={(e) => updateField('calendarLengthDays', e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="max-cost">Max cost</label>
          <input
            id="max-cost"
            type="number"
            min={0}
            step="0.01"
            value={form.maxCost}
            onChange={(e) => updateField('maxCost', e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="event-types">Event types (comma-separated)</label>
          <input
            id="event-types"
            type="text"
            value={form.eventTypes}
            onChange={(e) => updateField('eventTypes', e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="genres">Genres (comma-separated, music only)</label>
          <input
            id="genres"
            type="text"
            value={form.genres}
            onChange={(e) => updateField('genres', e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="start-after">Start after</label>
          <input
            id="start-after"
            type="time"
            value={form.startAfter}
            onChange={(e) => updateField('startAfter', e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="start-before">Start before</label>
          <input
            id="start-before"
            type="time"
            value={form.startBefore}
            onChange={(e) => updateField('startBefore', e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="model">Model override</label>
          <input
            id="model"
            type="text"
            value={form.model}
            onChange={(e) => updateField('model', e.target.value)}
          />
        </div>

        <button type="submit">Generate</button>
      </form>
    </section>
  )
}
