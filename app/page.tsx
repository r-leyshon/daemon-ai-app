"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { TextareaWithCopy } from "@/components/ui/textarea-with-copy"
import { Label } from "@/components/ui/label"
import { Plus, Loader2, X } from "lucide-react"

interface Daemon {
  id: string
  name: string
  prompt: string
  examples: Array<{ user: string; assistant: string }>
  guardrails?: string
  color: string
}

interface Suggestion {
  daemon_id: string
  daemon_name: string
  question: string
  span_text?: string
  start_index?: number
  end_index?: number
  color: string
  answer?: string
}

const SAMPLE_TEXT = `Language models are not yet good enough to be reliable thinking partners. Their frequent hallucinations make it difficult to know if their factual claims are valid. However, they excel at helping with creative tasks and brainstorming. The technology is advancing rapidly, with new models showing improved reasoning capabilities. Many researchers believe we're approaching a breakthrough in AI reliability. These systems could revolutionize how we work and learn, but we must remain cautious about their current limitations.`

const API_BASE = "http://localhost:8000"

export default function DaemonAIApp() {
  const [text, setText] = useState(SAMPLE_TEXT)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [daemons, setDaemons] = useState<Daemon[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedSuggestion, setSelectedSuggestion] = useState<Suggestion | null>(null)
  const [showAddDaemon, setShowAddDaemon] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [newDaemon, setNewDaemon] = useState({
    name: "",
    prompt: "",
    guardrails: "",
    color: "#f39c12",
  })
  const containerRef = useRef<HTMLDivElement>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  // Function to render highlighted text
  const renderHighlightedText = (text: string, suggestions: Suggestion[]) => {
    if (suggestions.length === 0) {
      return text
    }

    // Sort suggestions by start_index to process them in order
    const sortedSuggestions = suggestions
      .filter(s => s.start_index !== undefined && s.end_index !== undefined)
      .sort((a, b) => (a.start_index || 0) - (b.start_index || 0))

    if (sortedSuggestions.length === 0) {
      return text
    }

    const parts: Array<{ text: string; color?: string }> = []
    let lastIndex = 0

    sortedSuggestions.forEach((suggestion) => {
      const start = suggestion.start_index || 0
      const end = suggestion.end_index || 0

      // Add text before this highlight
      if (start > lastIndex) {
        parts.push({ text: text.slice(lastIndex, start) })
      }

      // Add highlighted text
      parts.push({
        text: text.slice(start, end),
        color: suggestion.color
      })

      lastIndex = end
    })

    // Add remaining text after last highlight
    if (lastIndex < text.length) {
      parts.push({ text: text.slice(lastIndex) })
    }

    return parts.map((part, index) => {
      if (part.color) {
        // Convert hex to rgba for better contrast
        const hexToRgba = (hex: string, alpha: number) => {
          const r = parseInt(hex.slice(1, 3), 16)
          const g = parseInt(hex.slice(3, 5), 16)
          const b = parseInt(hex.slice(5, 7), 16)
          return `rgba(${r}, ${g}, ${b}, ${alpha})`
        }
        
        return (
          <span
            key={index}
            style={{
              backgroundColor: hexToRgba(part.color, 0.4),
              color: '#000',
              padding: '2px 4px',
              borderRadius: '3px',
              fontWeight: '500'
            }}
          >
            {part.text}
          </span>
        )
      }
      return part.text
    })
  }

  // Test backend connection
  const testConnection = async () => {
    try {
      const response = await fetch(`${API_BASE}/health`)
      if (response.ok) {
        setConnectionError(null)
        return true
      } else {
        setConnectionError(`Backend responded with status: ${response.status}`)
        return false
      }
    } catch (error) {
      setConnectionError(`Cannot connect to backend at ${API_BASE}. Make sure the FastAPI server is running.`)
      return false
    }
  }

  // Load daemons on mount
  useEffect(() => {
    loadDaemons()
  }, [])

  const loadDaemons = async () => {
    try {
      const isConnected = await testConnection()
      if (!isConnected) return

      const response = await fetch(`${API_BASE}/daemons`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setDaemons(data.daemons)
      console.log(`Loaded ${data.daemons.length} daemons:`, data.daemons.map((d: Daemon) => d.name))
    } catch (error) {
      console.error("Error loading daemons:", error)
      setConnectionError(`Failed to load daemons: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // Get suggestion from a specific daemon
  const getSuggestionFromDaemon = async (daemon: Daemon) => {
    if (!text.trim()) return
    
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/suggestion/${daemon.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      const suggestion = data.suggestion
      
      // Add this suggestion to our list (or replace if it exists)
      setSuggestions(prev => {
        const filtered = prev.filter(s => s.daemon_id !== daemon.id)
        return [...filtered, suggestion]
      })
      setSelectedSuggestion(suggestion)
      
    } catch (error) {
      console.error("Error loading suggestion:", error)
      setConnectionError(`Failed to load suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleAnswerRequest = async (suggestion: Suggestion) => {
    if (suggestion.answer) return // Already has answer

    try {
      const response = await fetch(`${API_BASE}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          daemon_id: suggestion.daemon_id,
          question: suggestion.question,
          span_text: suggestion.span_text || "",
        }),
      })
      const data = await response.json()

      // Update suggestion with answer
      const updatedSuggestions = suggestions.map((s) =>
        s.daemon_id === suggestion.daemon_id && s.question === suggestion.question ? { ...s, answer: data.answer } : s,
      )
      setSuggestions(updatedSuggestions)
      setSelectedSuggestion({ ...suggestion, answer: data.answer })
    } catch (error) {
      console.error("Error getting answer:", error)
    }
  }

  const addDaemon = async () => {
    if (!newDaemon.name || !newDaemon.prompt) return

    try {
      const response = await fetch(`${API_BASE}/daemons`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newDaemon.name,
          prompt: newDaemon.prompt,
          guardrails: newDaemon.guardrails,
          color: newDaemon.color,
          examples: [],
        }),
      })

      if (response.ok) {
        setNewDaemon({ name: "", prompt: "", guardrails: "", color: "#f39c12" })
        setShowAddDaemon(false)
        await loadDaemons()
        // No need to call loadSuggestions() here, as the new daemon will be added to the list
      }
    } catch (error) {
      console.error("Error adding daemon:", error)
    }
  }

  const deleteDaemon = async (daemonId: string) => {
    try {
      const response = await fetch(`${API_BASE}/daemons/${daemonId}`, {
        method: "DELETE",
      })
      if (response.ok) {
        setDaemons(prev => prev.filter(d => d.id !== daemonId))
        setShowDeleteConfirm(null)
        // Clear suggestions from deleted daemon
        setSuggestions(prev => prev.filter(s => s.daemon_id !== daemonId))
        // Clear selected suggestion if it's from deleted daemon
        if (selectedSuggestion?.daemon_id === daemonId) {
          setSelectedSuggestion(null)
        }
      } else if (response.status === 404) {
        // Handle daemon not found
        setShowDeleteConfirm(null)
        setDeleteError("Daemon not found - it may have already been deleted.")
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
    } catch (error) {
      console.error("Error deleting daemon:", error)
      setConnectionError(`Failed to delete daemon: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // Clear all highlights
  const clearHighlights = () => {
    setSuggestions([])
    setSelectedSuggestion(null)
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Daemon AI Assistant</h1>
          <p className="text-gray-600">AI assistants that live alongside your text, offering contextual suggestions</p>
        </div>

        {connectionError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-red-500 rounded-full"></div>
              <h3 className="font-semibold text-red-800">Backend Connection Error</h3>
            </div>
            <p className="text-red-700 text-sm mt-1">{connectionError}</p>
            <p className="text-red-600 text-xs mt-2">
              Make sure to run: <code className="bg-red-100 px-1 rounded">cd backend && python main.py</code>
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={testConnection}
              className="mt-2 text-red-700 border-red-300 bg-transparent"
            >
              Test Connection
            </Button>
          </div>
        )}

        {!connectionError && daemons.length > 0 && (
          <div className="mb-6 p-3 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-green-800 text-sm font-medium">Connected • {daemons.length} daemons active</span>
            </div>
          </div>
        )}

        <div ref={containerRef} className="relative bg-white rounded-lg shadow-lg p-6">
          <div className="grid grid-cols-12 gap-6 h-full">
            {/* Text Content */}
            <div className="col-span-10 flex flex-col">
              <div className="flex-1 flex flex-col">
                {/* Show highlighted text when suggestions exist, otherwise show regular textarea */}
                {suggestions.length > 0 ? (
                  <div className="relative">
                    <div
                      className="w-full p-3 border border-gray-300 rounded-md bg-white leading-relaxed font-normal text-gray-900"
                      style={{ 
                        fontSize: '12pt', 
                        height: '500px', 
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap'
                      }}
                    >
                      {renderHighlightedText(text, suggestions)}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={clearHighlights}
                      className="absolute top-2 right-2"
                    >
                      Clear Highlights
                    </Button>
                  </div>
                ) : (
                  <TextareaWithCopy
                    id="text-input"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    className="leading-relaxed font-normal text-gray-900 border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                    style={{ fontSize: '12pt', height: '500px', paddingRight: '50px' }}
                    placeholder="Enter your text here..."
                    onCopyText={(copiedText) => {
                      console.log('Text copied:', copiedText.length, 'characters')
                    }}
                  />
                )}
              </div>
            </div>

            {/* Daemon Swatches */}
            <div className="col-span-2 relative">
              <div className="sticky top-6">
                <div className="mb-4">
                  <h3 className="font-semibold text-sm">Daemons</h3>
                </div>

                {loading && (
                  <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analyzing...
                  </div>
                )}

                <div className="space-y-3 mb-4">
                  {daemons.map((daemon) => {
                    const isDefaultDaemon = ["devil_advocate", "grammar_enthusiast", "clarity_coach"].includes(daemon.id)
                    const hasSuggestion = suggestions.some(s => s.daemon_id === daemon.id)
                    
                    return (
                      <div
                        key={daemon.id}
                        className="relative group flex items-center justify-between w-full py-1"
                      >
                        <div className="flex items-center">
                          <div
                            className={`w-6 h-6 rounded-full border-2 shadow-md cursor-pointer hover:scale-110 transition-transform ${
                              hasSuggestion ? 'ring-2 ring-offset-2' : 'border-gray-300'
                            }`}
                            style={{ 
                              backgroundColor: daemon.color,
                              minWidth: '24px',
                              minHeight: '24px',
                              '--tw-ring-color': hasSuggestion ? daemon.color : undefined
                            } as React.CSSProperties}
                            onClick={() => getSuggestionFromDaemon(daemon)}
                            title={daemon.name}
                          />
                          <div 
                            className="ml-3 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap"
                            style={{ color: daemon.color, marginLeft: '10px' }}
                          >
                            {daemon.name}
                          </div>
                        </div>
                        {!isDefaultDaemon && (
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                              onClick={(e) => {
                                e.stopPropagation()
                                setShowDeleteConfirm(daemon.id)
                              }}
                              title="Delete Daemon"
                            >
                              <X className="w-3 h-3" />
                            </Button>
                          </div>
                        )}
                      </div>
                    )
                  })}
                  
                  {/* Debug: Show if no daemons */}
                  {daemons.length === 0 && (
                    <div className="text-xs text-gray-500">No daemons loaded</div>
                  )}

                  {/* Add Daemon Button */}
                  <div className="relative group flex items-center py-1">
                    <div
                      className="w-6 h-6 rounded-full border-2 border-gray-300 bg-white shadow-md cursor-pointer hover:scale-110 transition-transform flex items-center justify-center"
                      style={{ 
                        minWidth: '24px',
                        minHeight: '24px'
                      }}
                      onClick={() => setShowAddDaemon(true)}
                      title="Add Daemon"
                    >
                      <Plus className="w-4 h-4 text-gray-600" />
                    </div>
                    <div 
                      className="ml-3 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap"
                      style={{ color: "#6b7280", marginLeft: '10px' }}
                    >
                      Add Daemon
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Suggestion Panel */}
          {selectedSuggestion && (
            <div className="mt-6 bg-white border rounded-lg shadow-sm p-6">
              <div className="flex items-start gap-4">
                <div
                  className="w-4 h-4 rounded-full mt-1 flex-shrink-0"
                  style={{ backgroundColor: selectedSuggestion.color }}
                />
                <div className="flex-1">
                  <h4 className="font-semibold mb-2">
                    {selectedSuggestion.daemon_name}
                  </h4>
                  <p className="text-gray-700 mb-4">{selectedSuggestion.question}</p>

                  {selectedSuggestion.answer ? (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-gray-800">{selectedSuggestion.answer}</p>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => handleAnswerRequest(selectedSuggestion)}
                      disabled={loading}
                    >
                      Get Answer
                    </Button>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedSuggestion(null)}
                >
                  ×
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Add Daemon Modal */}
        {showAddDaemon && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Add New Daemon</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="daemon-name">Name</Label>
                  <Input
                    id="daemon-name"
                    value={newDaemon.name}
                    onChange={(e) => setNewDaemon({ ...newDaemon, name: e.target.value })}
                    placeholder="e.g., Grammar Checker"
                  />
                </div>

                <div>
                  <Label htmlFor="daemon-prompt">Prompt/Purpose</Label>
                  <Textarea
                    id="daemon-prompt"
                    value={newDaemon.prompt}
                    onChange={(e) => setNewDaemon({ ...newDaemon, prompt: e.target.value })}
                    placeholder="Describe what this daemon should do..."
                    rows={3}
                  />
                </div>

                <div>
                  <Label htmlFor="daemon-guardrails">Guardrails (Optional)</Label>
                  <Textarea
                    id="daemon-guardrails"
                    value={newDaemon.guardrails}
                    onChange={(e) => setNewDaemon({ ...newDaemon, guardrails: e.target.value })}
                    placeholder="Any constraints or guidelines..."
                    rows={2}
                  />
                </div>

                <div>
                  <Label htmlFor="daemon-color">Color</Label>
                  <Input
                    id="daemon-color"
                    type="color"
                    value={newDaemon.color}
                    onChange={(e) => setNewDaemon({ ...newDaemon, color: e.target.value })}
                  />
                </div>

                <div className="flex gap-2 pt-4">
                  <Button onClick={addDaemon} className="flex-1">
                    Add Daemon
                  </Button>
                  <Button variant="outline" onClick={() => setShowAddDaemon(false)} className="flex-1">
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

                 {/* Delete Confirmation Modal */}
         {showDeleteConfirm && (
           <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
             <Card className="w-full max-w-md">
               <CardHeader>
                 <CardTitle>Confirm Deletion</CardTitle>
               </CardHeader>
               <CardContent className="space-y-4">
                 <p>Are you sure you want to delete this daemon? This action cannot be undone.</p>
                 <div className="flex gap-2">
                   <Button variant="outline" onClick={() => setShowDeleteConfirm(null)} className="flex-1">
                     Cancel
                   </Button>
                   <Button variant="destructive" onClick={() => deleteDaemon(showDeleteConfirm)} className="flex-1">
                     Delete
                   </Button>
                 </div>
               </CardContent>
             </Card>
           </div>
         )}

         {/* Delete Error Modal */}
         {deleteError && (
           <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
             <Card className="w-full max-w-md">
               <CardHeader>
                 <CardTitle className="text-amber-700">Cannot Delete Daemon</CardTitle>
               </CardHeader>
               <CardContent className="space-y-4">
                 <div className="flex items-start gap-3">
                   <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                     <span className="text-amber-600 text-sm font-semibold">!</span>
                   </div>
                   <p className="text-gray-700">{deleteError}</p>
                 </div>
                 <div className="flex justify-end">
                   <Button onClick={() => setDeleteError(null)}>
                     OK
                   </Button>
                 </div>
               </CardContent>
             </Card>
           </div>
         )}
      </div>
    </div>
  )
}
