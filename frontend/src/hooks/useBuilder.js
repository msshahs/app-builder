import { useState, useRef, useCallback } from 'react'
import { BuilderWebSocket } from '../utils/websocket'

export const AGENTS = [
    { id: 'planner', label: 'Planner', description: 'Analyzing prompt and creating plan' },
    { id: 'frontend', label: 'Frontend', description: 'Generating React components' },
    { id: 'backend', label: 'Backend', description: 'Generating Node.js APIs' },
    { id: 'database', label: 'Database', description: 'Generating Mongoose models' },
    { id: 'devops', label: 'DevOps', description: 'Generating Docker and CI/CD' },
    { id: 'review', label: 'Review', description: 'Checking consistency' },
]

const initialAgentState = () =>
    AGENTS.reduce((acc, a) => {
        acc[a.id] = {
            status: 'waiting',
            files: [],
            startTime: null,
            duration: null,
        }
        return acc
    }, {})

export function useBuilder() {
    const [status, setStatus] = useState('idle')
    const [agents, setAgents] = useState(initialAgentState)
    const [logs, setLogs] = useState([])
    const [generatedFiles, setGeneratedFiles] = useState({})
    const [selectedFile, setSelectedFile] = useState(null)
    const [activeTab, setActiveTab] = useState('logs')
    const [reviewResult, setReviewResult] = useState(null)
    const [fileContents, setFileContents] = useState({})
    const [stats, setStats] = useState({
        totalFiles: 0,
        agentsDone: 0,
        startTime: null,
        elapsed: null,
    })
    const wsRef = useRef(null)
    const timerRef = useRef(null)
    const agentsRef = useRef(agents)
    agentsRef.current = agents

    const addLog = useCallback((message, type = 'info') => {
        setLogs(prev => [...prev, {
            id: `${Date.now()}-${Math.random()}`,
            message,
            type,
            time: new Date().toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            }),
        }])
    }, [])

    const updateAgent = useCallback((id, updates) => {
        setAgents(prev => ({
            ...prev,
            [id]: { ...prev[id], ...updates },
        }))
    }, [])

    const handleEvent = useCallback((event) => {
        const { type, data } = event

        switch (type) {
            case 'agent_start': {
                updateAgent(data.agent, {
                    status: 'running',
                    startTime: Date.now(),
                })
                const meta = AGENTS.find(a => a.id === data.agent)
                addLog(`${meta?.label} agent started — ${meta?.description}`, 'info')
                break
            }

            case 'agent_complete': {
                const start = agentsRef.current[data.agent]?.startTime
                const duration = start
                    ? ((Date.now() - start) / 1000).toFixed(1)
                    : null
                updateAgent(data.agent, {
                    status: 'done',
                    files: data.files || [],
                    duration,
                })
                setStats(prev => ({ ...prev, agentsDone: prev.agentsDone + 1 }))
                addLog(
                    `${data.agent} complete — ${data.files?.length || 0} files generated (${duration}s)`,
                    'success'
                )
                if (data.files?.length) {
                    data.files.forEach(f => addLog(`  → ${f}`, 'file'))
                }
                break
            }

            case 'agent_error': {
                updateAgent(data.agent, { status: 'error' })
                addLog(`${data.agent} failed: ${data.error}`, 'error')
                break
            }

            case 'review_result': {
                setReviewResult(data)

                // Mark review agent as done
                updateAgent('review', {
                    status: 'done',
                    duration: ((Date.now() - agentsRef.current['review']?.startTime) / 1000).toFixed(1)
                })

                if (data.passed) {
                    addLog('Review passed — all checks green', 'success')
                } else {
                    const critical = data.issues?.filter(i => i.severity === 'critical').length || 0
                    addLog(
                        `Review found ${data.issues?.length} issues (${critical} critical)`,
                        'warning'
                    )
                }
                break
            }

            case 'generation_complete': {
                setGeneratedFiles(data.file_tree || {})
                setFileContents(data.all_files || {})
                setStatus('complete')
                setActiveTab('code')
                clearInterval(timerRef.current)
                const elapsed = ((Date.now() - stats.startTime) / 1000).toFixed(0)
                setStats(prev => ({
                    ...prev,
                    totalFiles: data.total_files,
                    elapsed,
                }))
                addLog(
                    `Generation complete — ${data.total_files} files in ${elapsed}s`,
                    'success'
                )
                break
            }

            case 'fatal_error': {
                setStatus('error')
                clearInterval(timerRef.current)
                addLog(`Fatal error: ${data.error}`, 'error')
                break
            }

            case 'disconnected': {
                clearInterval(timerRef.current)
                break
            }
        }
    }, [addLog, updateAgent, stats.startTime])

    const generate = useCallback(async (prompt) => {
        setStatus('generating')
        setAgents(initialAgentState())
        setGeneratedFiles({})
        setSelectedFile(null)
        setReviewResult(null)
        setLogs([])
        setActiveTab('logs')

        const startTime = Date.now()
        setStats({ totalFiles: 0, agentsDone: 0, startTime, elapsed: null })

        timerRef.current = setInterval(() => {
            setStats(prev => ({
                ...prev,
                elapsed: ((Date.now() - startTime) / 1000).toFixed(0),
            }))
        }, 1000)

        addLog(`Starting generation for: "${prompt}"`, 'info')
        addLog('Connecting to agent pipeline...', 'info')

        const ws = new BuilderWebSocket(handleEvent)
        wsRef.current = ws

        try {
            await ws.connect()
            addLog('Connected — pipeline starting', 'success')
            ws.send(prompt)
        } catch (err) {
            setStatus('error')
            clearInterval(timerRef.current)
            addLog(`Connection failed: ${err.message}`, 'error')
        }
    }, [handleEvent, addLog])

    const reset = useCallback(() => {
        wsRef.current?.disconnect()
        clearInterval(timerRef.current)
        setStatus('idle')
        setAgents(initialAgentState())
        setGeneratedFiles({})
        setSelectedFile(null)
        setReviewResult(null)
        setLogs([])
        setActiveTab('logs')
        setStats({ totalFiles: 0, agentsDone: 0, startTime: null, elapsed: null })
    }, [])

    return {
        status,
        agents,
        logs,
        generatedFiles,
        fileContents,
        selectedFile,
        setSelectedFile,
        activeTab,
        setActiveTab,
        reviewResult,
        stats,
        generate,
        reset,
    }
}