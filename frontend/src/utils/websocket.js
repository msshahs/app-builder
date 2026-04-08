export class BuilderWebSocket {
    constructor(onEvent) {
        this.onEvent = onEvent
        this.ws = null
        this.clientId = crypto.randomUUID().slice(0, 8)
    }

    connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(
                `ws://localhost:8000/api/ws/${this.clientId}`
            )

            this.ws.onopen = () => resolve()

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data)
                    this.onEvent(message)
                } catch (e) {
                    console.error('Failed to parse WS message:', e)
                }
            }

            this.ws.onerror = () => {
                reject(new Error('WebSocket connection failed'))
            }

            this.ws.onclose = () => {
                this.onEvent({ type: 'disconnected', data: {} })
            }
        })
    }

    send(prompt) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ prompt }))
        }
    }

    disconnect() {
        this.ws?.close()
    }
}