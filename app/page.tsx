"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { TextareaWithCopy } from "@/components/ui/textarea-with-copy"
import { Label } from "@/components/ui/label"
import { Plus, Loader2, X } from "lucide-react"
import { getApiBaseUrl } from '../lib/config'

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
  suggested_fix?: string
  is_outdated?: boolean
}

const SAMPLE_TEXT = `Language models are not yet good enough to be reliable thinking partners. Their frequent hallucinations make it difficult to know if their factual claims are valid. However, they excel at helping with creative tasks and brainstorming. The technology is advancing rapidly, with new models showing improved reasoning capabilities. Many researchers believe we're approaching a breakthrough in AI reliability. These systems could revolutionize how we work and learn, but we must remain cautious about their current limitations.`

const API_BASE = getApiBaseUrl()

export default function DaemonAIApp() {
  const [text, setText] = useState(SAMPLE_TEXT)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [daemons, setDaemons] = useState<Daemon[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedSuggestion, setSelectedSuggestion] = useState<Suggestion | null>(null)
  const [suggestionQueue, setSuggestionQueue] = useState<Suggestion[]>([])
  const [showAddDaemon, setShowAddDaemon] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [showSuggestedFix, setShowSuggestedFix] = useState(false)
  const [newDaemon, setNewDaemon] = useState({
    name: "",
    prompt: "",
    guardrails: "",
    color: "#f39c12",
  })
  const containerRef = useRef<HTMLDivElement>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  // Convert hex to rgba for better contrast
  const hexToRgba = (hex: string, alpha: number) => {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }

  // Function to render highlighted text
  const renderHighlightedText = (text: string, suggestions: Suggestion[], selectedSuggestion: Suggestion | null) => {
    if (suggestions.length === 0) {
      return text
    }

    // Only show highlight for the currently selected suggestion
    if (!selectedSuggestion || selectedSuggestion.start_index === undefined || selectedSuggestion.end_index === undefined) {
      return text
    }

    const start = selectedSuggestion.start_index
    const end = selectedSuggestion.end_index

    return (
      <>
        {text.slice(0, start)}
        <span
          style={{
            backgroundColor: hexToRgba(selectedSuggestion.color, 0.4),
            color: '#000',
            cursor: 'pointer'
          }}
          onClick={() => {
            // Find the suggestion for this highlighted text
            const suggestion = suggestions.find(s => s.daemon_id === selectedSuggestion.daemon_id)
            if (suggestion) {
              setSelectedSuggestion(suggestion)
            }
          }}
        >
          {text.slice(start, end)}
        </span>
        {text.slice(end)}
      </>
    )
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
      
      // Add this suggestion to our list (allow multiple from same daemon)
      setSuggestions(prev => [...prev, suggestion])
      
      // Add to suggestion queue (allow multiple from same daemon)
      setSuggestionQueue(prev => {
        const newQueue = [...prev, suggestion]
        
        // Always select the latest suggestion (this one)
        setSelectedSuggestion(suggestion)
        setShowSuggestedFix(false) // Keep collapsed by default for new suggestions
        
        return newQueue
      })
      
    } catch (error) {
      console.error("Error loading suggestion:", error)
      setConnectionError(`Failed to load suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleApplySuggestion = async (suggestion: Suggestion) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/apply-suggestion`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_text: text,
          suggestion_question: suggestion.question,
          span_text: suggestion.span_text,
          start_index: suggestion.start_index,
          end_index: suggestion.end_index,
          daemon_name: suggestion.daemon_name
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      setText(data.improved_text)

      // Remove the applied suggestion and mark others as outdated
      setSuggestions(prev => prev.filter(s => s !== suggestion).map(s => ({ ...s, is_outdated: true })))
      setSuggestionQueue(prev => {
        const currentIndex = prev.findIndex(s => s === suggestion)
        const newQueue = prev.filter(s => s !== suggestion).map(s => ({ ...s, is_outdated: true }))
        
        // Select the previous suggestion in the queue, or the first one if we were at the beginning
        let nextIndex = currentIndex - 1
        if (nextIndex < 0) {
          nextIndex = 0
        }
        if (nextIndex >= newQueue.length) {
          nextIndex = newQueue.length - 1
        }
        
        const nextSuggestion = newQueue.length > 0 ? newQueue[nextIndex] : null
        setSelectedSuggestion(nextSuggestion)
        
        return newQueue
      })
    } catch (error) {
      console.error("Error applying suggestion:", error)
      setConnectionError(`Failed to apply suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleRejectSuggestion = (suggestion: Suggestion) => {
    // Remove only this specific suggestion from both arrays
    setSuggestions(prev => prev.filter(s => s !== suggestion))
    setSuggestionQueue(prev => {
      const newQueue = prev.filter(s => s !== suggestion)
      
      // Select the next suggestion in the queue, or null if empty
      if (newQueue.length > 0) {
        setSelectedSuggestion(newQueue[0])
      } else {
        setSelectedSuggestion(null)
      }
      
      return newQueue
    })
  }

  const handleDismissSuggestion = (suggestion: Suggestion) => {
    // Remove only this specific suggestion from both arrays
    setSuggestions(prev => prev.filter(s => s !== suggestion))
    setSuggestionQueue(prev => {
      const newQueue = prev.filter(s => s !== suggestion)
      
      // Select the next suggestion in the queue, or null if empty
      if (newQueue.length > 0) {
        setSelectedSuggestion(newQueue[0])
      } else {
        setSelectedSuggestion(null)
      }
      
      return newQueue
    })
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
        setSuggestionQueue(prev => prev.filter(s => s.daemon_id !== daemonId))
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
    setSuggestionQueue([])
    setSelectedSuggestion(null)
  }

  // Navigation functions for suggestion queue
  const goToNextSuggestion = () => {
    if (!selectedSuggestion || suggestionQueue.length <= 1) return
    
    const currentIndex = suggestionQueue.findIndex(s => s === selectedSuggestion)
    const nextIndex = (currentIndex + 1) % suggestionQueue.length
    setSelectedSuggestion(suggestionQueue[nextIndex])
  }

  const goToPreviousSuggestion = () => {
    if (!selectedSuggestion || suggestionQueue.length <= 1) return
    
    const currentIndex = suggestionQueue.findIndex(s => s === selectedSuggestion)
    const prevIndex = currentIndex === 0 ? suggestionQueue.length - 1 : currentIndex - 1
    setSelectedSuggestion(suggestionQueue[prevIndex])
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
            <div className="col-span-10 flex flex-col relative">
              <div className="flex-1 flex flex-col">
                {/* Show highlighted text when suggestions exist, otherwise show regular textarea */}
                {suggestions.length > 0 ? (
                  <div
                    className="w-full border border-gray-300 rounded-md bg-white leading-relaxed font-normal text-gray-900 relative"
                    style={{ 
                      fontSize: '12pt', 
                      height: '500px', 
                      overflowY: 'auto',
                      overflowX: 'hidden',
                      whiteSpace: 'pre-wrap',
                      padding: '12px 12px 12px 12px',
                      lineHeight: '1.6'
                    }}
                  >
                    {renderHighlightedText(text, suggestions, selectedSuggestion)}
                  </div>
                ) : (
                  <TextareaWithCopy
                    id="text-input"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    className="leading-relaxed font-normal text-gray-900 border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                    style={{ 
                      fontSize: '12pt', 
                      height: '500px', 
                      padding: '12px 12px 12px 12px',
                      paddingRight: '50px',
                      lineHeight: '1.6'
                    }}
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
                <div className="mb-4 flex items-center gap-2">
                  <h3 className="font-semibold text-sm">Daemons</h3>
                  {loading && (
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Analysing...
                    </div>
                  )}
                  {!loading && daemons.length === 0 && (
                    <div className="text-xs text-gray-500">Loading</div>
                  )}
                </div>

                <div className="space-y-3 mb-4">
                  {daemons.map((daemon) => {
                    const isDefaultDaemon = ["devil_advocate", "grammar_enthusiast", "clarity_coach"].includes(daemon.id)
                    
                    // Debug logging
                    console.log(`Daemon ${daemon.name}: color=${daemon.color}`)
                    
                    return (
                      <div
                        key={daemon.id}
                        className="relative group flex items-center justify-between w-full py-1"
                      >
                        <div className="flex items-center">
                          <div
                            className="daemon-swatch w-6 h-6 rounded-full border-2 border-gray-300 shadow-md cursor-pointer hover:scale-110 transition-transform"
                            style={{ 
                              backgroundColor: daemon.color,
                              minWidth: '24px',
                              minHeight: '24px'
                            } as React.CSSProperties}
                            data-daemon-color={daemon.color}
                            data-daemon-id={daemon.id}
                            onClick={() => getSuggestionFromDaemon(daemon)}
                            title={`${daemon.name} (${daemon.color})`}
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

                {/* Clear Highlights Button */}
                {suggestions.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={clearHighlights}
                      className="w-full text-xs"
                    >
                      Clear All Highlights
                    </Button>
                  </div>
                )}
              </div>
              
              {/* Suggestion Panel - Floating above text area */}
              {selectedSuggestion && (
                <div 
                  className="absolute bg-white border rounded-lg shadow-lg p-3 z-30"
                  style={{
                    position: 'absolute',
                    bottom: '10px',
                    right: '195px',
                    width: '450px',
                    pointerEvents: 'auto'
                  }}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="w-3 h-3 rounded-full mt-1 flex-shrink-0"
                      style={{ backgroundColor: selectedSuggestion.color }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-sm">
                          {selectedSuggestion.daemon_name}
                        </h4>
                        {suggestionQueue.length > 1 && (
                          <div className="flex items-center gap-1 text-xs text-gray-500">
                            <span>
                              {suggestionQueue.findIndex(s => s === selectedSuggestion) + 1} of {suggestionQueue.length}
                            </span>
                            <div className="flex gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={goToPreviousSuggestion}
                                className="h-5 w-5 p-0 text-gray-400 hover:text-gray-600"
                                title="Previous suggestion"
                              >
                                ←
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={goToNextSuggestion}
                                className="h-5 w-5 p-0 text-gray-400 hover:text-gray-600"
                                title="Next suggestion"
                              >
                                →
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                      <p className="text-gray-700 text-sm mb-3">{selectedSuggestion.question}</p>

                      {/* Show suggested fix if available */}
                      {selectedSuggestion.suggested_fix && (
                        <div 
                          className="mb-3 rounded text-sm border overflow-hidden"
                          style={{
                            backgroundColor: hexToRgba(selectedSuggestion.color, 0.1),
                            borderColor: hexToRgba(selectedSuggestion.color, 0.3)
                          }}
                        >
                          <div 
                            className="flex items-center justify-between p-2 cursor-pointer hover:bg-opacity-20 transition-colors"
                            onClick={() => setShowSuggestedFix(!showSuggestedFix)}
                            style={{ 
                              color: selectedSuggestion.color,
                              backgroundColor: hexToRgba(selectedSuggestion.color, 0.05)
                            }}
                          >
                            <div className="font-medium">Suggested Fix</div>
                            <div 
                              className="text-xs transition-transform duration-200"
                              style={{ 
                                transform: showSuggestedFix ? 'rotate(90deg)' : 'rotate(0deg)'
                              }}
                            >
                              ▶
                            </div>
                          </div>
                          <div 
                            className="transition-all duration-200 ease-in-out overflow-hidden"
                            style={{
                              maxHeight: showSuggestedFix ? '200px' : '0px',
                              opacity: showSuggestedFix ? 1 : 0
                            }}
                          >
                            <div 
                              className="px-2 pb-2"
                              style={{ color: selectedSuggestion.color }}
                            >
                              {selectedSuggestion.suggested_fix}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Show outdated indicator */}
                      {selectedSuggestion.is_outdated && (
                        <div className="mb-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm">
                          <div className="text-yellow-700 font-medium">⚠️ This suggestion may be outdated due to recent text changes</div>
                        </div>
                      )}

                      {/* Show different buttons based on suggestion type */}
                      {selectedSuggestion && (
                        <div className="flex gap-2 mt-3">
                          {selectedSuggestion.question.includes("No specific issues found") ? (
                            <Button
                              size="sm"
                              onClick={() => handleDismissSuggestion(selectedSuggestion)}
                              className="text-xs bg-gray-600 hover:bg-gray-700 text-white border-gray-600"
                            >
                              Dismiss
                            </Button>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                onClick={() => handleApplySuggestion(selectedSuggestion)}
                                className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white border-emerald-600"
                                disabled={selectedSuggestion.is_outdated}
                              >
                                Fix
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleRejectSuggestion(selectedSuggestion)}
                                className="text-xs bg-red-600 hover:bg-red-700 text-white border-red-600"
                              >
                                Reject
                              </Button>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>


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
