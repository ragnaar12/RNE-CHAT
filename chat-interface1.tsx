"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Send, ArrowLeft, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useLanguage } from "@/hooks/use-language"
import { useTranslation } from "@/hooks/use-translation"
import { TypingIndicator } from "@/components/typing-indicator"
import axios from "axios"

interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
}

interface ChatInterfaceProps {
  onBack: () => void
}

export function ChatInterfaceHelp({ onBack }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "Bienvenue ! Comment puis-je vous aider aujourd'hui ?",
      isUser: false,
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const { language } = useLanguage()
  const { t } = useTranslation()

  // API configuration

const API_ENDPOINT = "http://localhost:8000/chat";


  // Scroll to bottom
  const scrollToBottom = () => {
    if (chatContainerRef.current && messagesEndRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
  }

  // Scroll when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Update welcome message based on language
  useEffect(() => {
    const welcomeMessage: Message = {
      id: "welcome",
      content: t("chat.welcome") || "Bienvenue ! Comment puis-je vous aider aujourd'hui ?",
      isUser: false,
      timestamp: new Date(),
    }
    setMessages((prev) =>
      prev[0]?.id === "welcome"
        ? [welcomeMessage, ...prev.slice(1)]
        : [welcomeMessage, ...prev]
    )
  }, [language, t])

  // Send message to server
  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return

    const newUserMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      isUser: true,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, newUserMessage])
    setInputValue("")
    setIsLoading(true)

    try {
      const response = await axios.post(API_ENDPOINT, {
        prompt: inputValue,
        style: "concise",
        session_id: "default",
        short_response: false,
      }, {
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
      })

      console.log("API Response:", response.data)

      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: response.data.response || t("chatbot.no_data") || "Aucune réponse reçue du serveur.",
        isUser: false,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botResponse])
    } catch (error) {
      console.error("Error calling API:", error)
      let errorMessageContent = t("chatbot.error") || "Désolé, une erreur s'est produite."
      if (axios.isAxiosError(error)) {
        errorMessageContent += error.response
          ? `: ${error.response.status} ${error.response.statusText} - ${JSON.stringify(error.response.data)}`
          : `: ${error.message}`
      } else {
        errorMessageContent += `: ${error instanceof Error ? error.message : "Erreur inconnue"}`
      }

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: errorMessageContent,
        isUser: false,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      scrollToBottom()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="h-screen flex flex-col bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-gray-900 dark:to-gray-800 p-4"
    >
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm rounded-t-lg overflow-hidden">
        <div className="flex items-center justify-between px-6 py-5 bg-indigo-600 text-white">
          <button onClick={onBack} className="flex items-center space-x-2 hover:text-indigo-200 transition-colors">
            <ArrowLeft className="w-4 h-4" />
            <span>{t("chat.back") || "Retour"}</span>
          </button>

          <div className="flex items-center">
            <div className="bg-indigo-800 w-10 h-10 rounded-full flex items-center justify-center mr-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <div>
              <h2 className="font-bold text-lg">{t("chat.title") || "Chatbot"}</h2>
              <p className="text-xs text-indigo-200">En ligne • Tunisie</p>
            </div>
          </div>

          <div className="flex space-x-2">
            <button className="p-2 rounded-full hover:bg-indigo-500 transition">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Zone de Messages - Scroll Interne */}
      <div
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-6 bg-white dark:bg-gray-800 space-y-4"
      >
        <div className="max-w-3xl mx-auto w-full">
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className={`flex ${message.isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-md px-4 py-3 rounded-2xl ${
                    message.isUser
                      ? "bg-indigo-600 text-white rounded-tr-none"
                      : "bg-gray-100 text-gray-800 rounded-tl-none dark:bg-gray-700 dark:text-white"
                  }`}
                >
                  <p>{message.content}</p>
                  <div
                    className={`text-xs mt-1 ${
                      message.isUser ? "text-indigo-200" : "text-gray-500 dark:text-gray-400"
                    }`}
                  >
                    {new Date(message.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Zone d'entrée fixe */}
      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4 rounded-b-lg">
        <div className="flex items-center space-x-2 max-w-3xl mx-auto">
          <div className="flex-1 flex items-center bg-gray-100 dark:bg-gray-700 rounded-2xl px-4 py-2">
            <button className="p-2 text-gray-500 hover:text-indigo-600">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </button>
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t("chat.placeholder") || "Tapez votre message..."}
              disabled={isLoading}
              className="flex-1 bg-transparent outline-none text-gray-800 dark:text-white"
            />
            <button className="p-2 text-gray-500 hover:text-indigo-600">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
          </div>
          <Button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="ml-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-2 rounded-2xl flex items-center transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                {t("chat.send") || "Envoyer"}
                <Send className="h-5 w-5 ml-1" />
              </>
            )}
          </Button>
        </div>
      </div>
    </motion.div>
  )
}
