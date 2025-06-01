"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/hooks/use-translation";
import { ChatInterface } from "@/components/chat-interface";
import { useRouter } from "next/navigation";
import type { ChatMessageProps } from "@/types/chat";
import Link from "next/link";
import { ChatInterfaceHelp } from "./chat-interface1";

export default function ChoiceInterface({ onBack }: ChatMessageProps) {
  const [selectedOption, setSelectedOption] = useState<
    "check" | "suggest" | null
  >(null);
  const { t } = useTranslation();
  const router = useRouter();

  if (selectedOption === "check") {
    return <ChatInterface onBack={() => setSelectedOption(null)} />;
  }

  if (selectedOption === "suggest") {
    return <ChatInterfaceHelp onBack={() => setSelectedOption(null)} />;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="container mx-auto px-4 py-20 text-center"
    >
      <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-6">
        {t("chat.choice.title")}
      </h2>
      <p className="text-lg text-gray-600 dark:text-gray-300 mb-10 max-w-2xl mx-auto">
        {t("chat.choice.subtitle")}
      </p>

      <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
        {/* Option 1 - Vérification */}
        <motion.div
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.98 }}
          className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg hover:shadow-xl cursor-pointer transition-all"
          onClick={() => setSelectedOption("check")}
        >
          <div className="text-5xl mb-4">🔍</div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            {t("chat.choice.option1.title")}
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            {t("chat.choice.option1.description")}
          </p>
        </motion.div>

        {/* Option 2 - Suggestions */}
        <motion.div
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.98 }}
          className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg hover:shadow-xl cursor-pointer transition-all"
          onClick={() => setSelectedOption("suggest")}
        >
          <div className="text-5xl mb-4">💡</div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            {t("chat.choice.option2.title")}
          </h3>
          <p className="text-gray-600 dark:text-gray-300">
            {t("chat.choice.option2.description")}
          </p>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-10"
      >
       
          <Button
            variant="ghost"
            className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
            onClick={onBack}
          >
            {t("chat.choice.back")}
          </Button>

      </motion.div>
    </motion.div>
  );
}
