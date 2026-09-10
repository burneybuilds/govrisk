import { useState, useEffect } from 'react';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import { addProjectUpdate, updateProjectUpdate } from '../../services/api';

const UPDATE_TYPES = [
  { value: 'GENERAL', label: 'General' },
  { value: 'PROGRESS', label: 'Progress' },
  { value: 'RISK', label: 'Risk' },
  { value: 'FINANCIAL', label: 'Financial' },
  { value: 'MILESTONE', label: 'Milestone' },
  { value: 'FIELD_VISIT', label: 'Field Visit' },
];

export default function AddUpdateModal({
  projectId,
  open,
  initial,
  onClose,
  onSaved,
}: {
  projectId: string;
  open: boolean;
  initial?: any;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!initial;
  const [updateType, setUpdateType] = useState('GENERAL');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setUpdateType(initial?.updateType || 'GENERAL');
      setContent(initial?.content || '');
      setError('');
      setSaving(false);
    }
  }, [open, initial]);

  if (!open) return null;

  async function handleSubmit() {
    setError('');
    if (!content.trim()) {
      setError('Message is required');
      return;
    }
    setSaving(true);
    try {
      const payload = { updateType, content: content.trim() };
      if (isEdit) {
        await updateProjectUpdate(projectId, initial.id, payload);
      } else {
        await addProjectUpdate(projectId, payload);
      }
      onSaved();
      onClose();
    } catch (e: any) {
      setError(e.message || 'Failed to save update');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <X className="h-5 w-5" />
        </button>

        <h3 className="mb-1 text-lg font-semibold text-navy-900">
          {isEdit ? 'Edit Note / Update' : 'Add Note / Update'}
        </h3>
        <p className="mb-5 text-sm text-gray-500">
          {isEdit
            ? 'Update the recorded note for this project.'
            : 'Record a note or status update for this project.'}
        </p>

        {error && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              Update Type
            </label>
            <select
              value={updateType}
              onChange={(e) => setUpdateType(e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-200 bg-white px-3.5 text-sm text-gray-700 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            >
              {UPDATE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              Message
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your note or update..."
              rows={5}
              className="w-full rounded-lg border border-gray-200 bg-white px-3.5 py-2.5 text-sm text-gray-700 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              isEdit ? 'Save Update' : 'Add Update'
            )}
          </button>
          <button
            onClick={onClose}
            disabled={saving}
            className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-navy-900 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}