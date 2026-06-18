import { useState, useRef } from 'react'

const ACCEPTED = '.csv,.xlsx,.xls,.pdf'
const ACCEPTED_LABELS = ['CSV', 'Excel (.xlsx/.xls)', 'PDF']

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

export default function FileUpload({ profile, onAnalyze, onBack, error }) {
  const [files, setFiles] = useState([])
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)

  const addFiles = (newFiles) => {
    const arr = Array.from(newFiles)
    setFiles(prev => {
      const names = new Set(prev.map(f => f.name))
      return [...prev, ...arr.filter(f => !names.has(f.name))]
    })
  }

  const removeFile = (name) => setFiles(f => f.filter(x => x.name !== name))

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }

  const handleSubmit = () => {
    if (!files.length) return
    onAnalyze(files)
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        {profile?.company_name && (
          <div className="text-gold text-xs font-bold tracking-widest mb-2 uppercase">
            {profile.company_name}
          </div>
        )}
        <h2 className="text-2xl font-bold text-white mb-2">Upload Business Data</h2>
        <p className="text-slate-400 text-sm max-w-md mx-auto">
          Upload your financial files. More data = more specific findings.
        </p>
      </div>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
          transition-all duration-200
          ${dragging
            ? 'border-gold bg-gold/10'
            : 'border-white/10 bg-navy-card hover:border-gold/30 hover:bg-gold/5'
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          className="hidden"
          onChange={e => addFiles(e.target.files)}
        />
        <div className="text-4xl mb-4">📂</div>
        <p className="text-white font-semibold mb-1">Drop files here or click to browse</p>
        <p className="text-slate-500 text-xs">
          Accepted: {ACCEPTED_LABELS.join(' · ')}
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map(f => (
            <div
              key={f.name}
              className="flex items-center gap-3 bg-navy-card border border-white/[0.08] rounded-xl px-4 py-3"
            >
              <span className="text-gold text-sm">📄</span>
              <div className="flex-1 min-w-0">
                <div className="text-white text-sm font-medium truncate">{f.name}</div>
                <div className="text-slate-500 text-xs">{formatSize(f.size)}</div>
              </div>
              <button
                onClick={() => removeFile(f.name)}
                className="text-slate-500 hover:text-red-400 text-lg leading-none transition-colors ml-2"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
        <button
          onClick={handleSubmit}
          disabled={!files.length}
          className={`
            w-full sm:w-auto px-8 py-3 rounded-xl font-bold text-sm transition-all
            ${files.length
              ? 'bg-gold hover:bg-gold-light text-navy cursor-pointer'
              : 'bg-white/5 text-slate-600 cursor-not-allowed'
            }
          `}
        >
          Run Analysis ({files.length} {files.length === 1 ? 'file' : 'files'})
        </button>
        <button
          onClick={onBack}
          className="text-slate-500 text-sm hover:text-slate-300 transition-colors"
        >
          ← Edit profile
        </button>
      </div>

      {/* Agent roster */}
      <div className="mt-10 pt-8 border-t border-white/[0.06]">
        <p className="text-xs text-slate-600 text-center mb-4 tracking-wider uppercase">
          11 Agents Standing By
        </p>
        <div className="flex flex-wrap gap-2 justify-center">
          {[
            'CEO Orchestrator', 'Financial Forensics', 'Accounting', 'Auditor',
            'Operations', 'Logistics', 'Sales', 'Marketing',
            'Human Resources', 'Procurement', 'Strategy',
          ].map(a => (
            <span
              key={a}
              className="bg-gold/8 border border-gold/20 text-gold text-xs px-3 py-1 rounded-full font-medium"
            >
              {a}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
