"use client"

import { motion } from "framer-motion"
import { Bot, User } from "lucide-react"

interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
}

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3 }}
      className={`flex ${message.isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`flex items-start space-x-2 max-w-xs md:max-w-md ${
          message.isUser ? "flex-row-reverse space-x-reverse" : ""
        }`}
      >
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center ${
            message.isUser
              ? "bg-blue-600 text-white"
              : "bg-blue-100 dark:bg-gray-700 text-blue-900 dark:text-gray-300"
          }`}
        >
          {message.isUser ? (
            <User className="w-4 h-4" />
          ) : (
            <Bot className="w-4 h-4" />
          )}
        </div>
        <motion.div
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.2, delay: 0.1 }}
          className={`px-4 py-2 rounded-2xl shadow-md ${
            message.isUser
              ? "bg-blue-600 text-white rounded-tr-none"
              : "bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-600 rounded-tl-none"
          }`}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          <p
            className={`text-xs mt-1 ${
              message.isUser ? "text-blue-100" : "text-gray-500 dark:text-gray-400"
            }`}
          >
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </motion.div>
      </div>
    </motion.div>
  )
}
