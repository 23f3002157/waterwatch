import os
import time
import textwrap
import requests
from colorama import Fore, Style, init
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from dotenv import load_dotenv

init(autoreset=True)

class CommunityWaterWatchChatbot:
    def __init__(self, file_path=None, directory_path=None, chunk_size=1000, chunk_overlap=150, vector_store_path="./vector_store"):
        self.file_path = file_path
        self.directory_path = directory_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vectorstore = None
        self.chain = None
        self.chat_history = []
        self.company_name = "Community Water Watch"
        self.bot_name = "WaterWatchBot"
        self.vector_store_path = vector_store_path
        self.embedding_model = "BAAI/bge-small-en-v1.5"
        self.gemini_model = "gemini-1.5-pro"
        self.last_request_time = 0
        self.min_request_interval = 6  # Rate limiting interval in seconds
        self.system_message = """
        You are WaterWatchBot, an AI assistant for Community Water Watch platform.
        You help users report water-related issues and provide guidance on water quality, conservation, and safety.
        Answer questions based on both the provided document context and general knowledge.
        Be helpful, concise, and accurate in your responses.
        Never mention sources or citations in your responses.
        Always respond in plain text format without metadata.
        """

    def display_welcome_message(self):
        print(f"\n{Fore.CYAN}{'=' * 60}")
        print(f"{Fore.BLUE}{' ' * 12}Welcome to {self.company_name} Assistant{' ' * 12}")
        print(f"{Fore.CYAN}{'=' * 60}")
        print(f"{Fore.WHITE}I'm {self.bot_name}, your AI assistant powered by Google's Gemini.")
        print(f"{Fore.WHITE}Type 'help' for assistance or 'exit' to quit.")
        print(f"{Fore.CYAN}{'=' * 60}\n")

    def load_document(self):
        documents = []
        encodings = ['utf-8', 'latin-1', 'cp437']
        if self.file_path:
            for encoding in encodings:
                try:
                    loader = TextLoader(self.file_path, encoding=encoding)
                    documents = loader.load()
                    return documents
                except UnicodeDecodeError:
                    continue
            raise ValueError("Failed to load document with tried encodings")
        elif self.directory_path:
            try:
                loader = DirectoryLoader(self.directory_path, glob="**/*.txt", loader_cls=TextLoader)
                documents = loader.load()
                return documents
            except Exception as e:
                raise ValueError(f"Failed to load documents from directory: {str(e)}")
        else:
            sample_data = """
            # Community Water Watch Knowledge Base

            ## Water Quality Issues
            - Brown water: May indicate rust in pipes or sediment
            - Blue/green tint: Could be copper contamination
            - Rotten egg smell: Hydrogen sulfide gas
            - Chlorine smell: Disinfection byproducts
            - Metallic taste: Could indicate presence of metals like iron, copper, zinc, or lead
            - Cloudy appearance: Might be air bubbles or suspended particles

            ## Reporting Procedures
            1. Document the issue with photos
            2. Note the time and location
            3. Check if neighbors are experiencing similar issues
            4. Submit report through app or website
            5. Follow up with local water authority if necessary
            6. Keep samples of contaminated water if possible

            ## Conservation Tips
            - Fix leaky faucets promptly
            - Install low-flow fixtures
            - Collect rainwater for gardens
            - Water plants during cooler hours
            - Use drought-resistant landscaping
            - Take shorter showers
            - Run full loads in washing machines and dishwashers

            ## Emergency Contacts
            - Water utility emergency line: 555-WATER
            - Environmental protection hotline: 555-ENVIRO
            - Public health department: 555-HEALTH
            - Poison control center: 800-222-1222

            ## Water Quality Standards
            - pH level should be between 6.5 and 8.5
            - Total dissolved solids (TDS) below 500 mg/L
            - Lead below 0.015 mg/L
            - Copper below 1.3 mg/L
            - No detectable E. coli or fecal coliform bacteria

            ## Common Water Testing Methods
            - Home test kits for basic parameters
            - Professional laboratory testing for comprehensive analysis
            - Continuous monitoring systems for municipal supplies
            - Well water should be tested annually
            """
            return [Document(page_content=sample_data, metadata={"source": "built-in data"})]

    def _rate_limit(self):
        """Enforce rate limiting to prevent API quota exceeded errors."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            # Silently wait without printing
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def initialize_pipeline(self):
        if not os.getenv("GOOGLE_API_KEY"):
            print(f"{Fore.RED}❌ GOOGLE_API_KEY is missing! Set it in your .env file or environment variables.")
            return False
        
        if os.path.exists(self.vector_store_path) and os.path.isdir(self.vector_store_path):
            try:
                embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
                self.vectorstore = FAISS.load_local(
                    self.vector_store_path, 
                    embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                self._create_vectorstore()
        else:
            self._create_vectorstore()
            
        try:
            llm = ChatGoogleGenerativeAI(
                model=self.gemini_model,
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                temperature=0.5,
                max_output_tokens=512,
                top_k=40,
                top_p=0.95
            )
            
            # Test the LLM to ensure connectivity
            self._rate_limit()
            test_result = llm.invoke("Give me a one-word response: test")
            
        except Exception as e:
            print(f"{Fore.RED}Error initializing Gemini model: {str(e)}")
            print(f"{Fore.YELLOW}Possible causes: Invalid API key, network issues, or unsupported model.")
            print(f"{Fore.YELLOW}Please check your API key and try again.")
            return False
        
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")
        
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 4}),
            memory=memory,
            return_source_documents=True,
        )
        return True

    def _create_vectorstore(self):
        documents = self.load_document()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunks = text_splitter.split_documents(documents)
        embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        
        self.vectorstore = FAISS.from_documents(chunks, embeddings)
        
        os.makedirs(self.vector_store_path, exist_ok=True)
        self.vectorstore.save_local(self.vector_store_path)
        

    def format_response(self, text):
        # Clean up the response by removing source references and other metadata
        text = text.split("\n\nSources:")[0]  # Remove sources section if present
        text = text.strip()
        return textwrap.fill(text, width=80)

    def handle_special_commands(self, query):
        query_lower = query.lower().strip()
        if query_lower == "help":
            return "Available commands:\n- 'help': Show this help message\n- 'clear': Clear the conversation history\n- 'exit': Quit the chatbot\n- 'about': Information about the Community Water Watch platform\n- 'status': Check the API connection status"
        elif query_lower == "clear":
            self.chat_history = []
            return "Conversation history cleared."
        elif query_lower == "about":
            return "Community Water Watch Platform is an AI-powered system designed to help communities report and track water-related issues. You can report problems, get information about water quality, and learn best practices for water conservation."
        elif query_lower == "status":
            try:
                # Quick API check
                self._rate_limit()
                test_llm = ChatGoogleGenerativeAI(
                    model=self.gemini_model,
                    google_api_key=os.getenv("GOOGLE_API_KEY"),
                    temperature=0.1,
                    max_output_tokens=10
                )
                test_llm.invoke("Test")
                return "API connection is working properly."
            except Exception as e:
                return f"API connection issue: {str(e)}"
        return None

    def chat(self, query):
        special_response = self.handle_special_commands(query)
        if special_response:
            return special_response
        
        try:
            # Apply rate limiting before making API calls
            self._rate_limit()
            
            # Try the retrieval-based approach first
            response = self.chain.invoke({"question": query})
            answer = response.get("answer", "").strip()
            
            # Enhanced fallback mechanism
            if (not answer or 
                "I don't know" in answer or 
                "I don't have" in answer or
                "I cannot" in answer or
                len(answer) < 20):
                
                self._rate_limit()
                
                # Create context from chat history
                history_context = ""
                if self.chat_history:
                    history_context = "Previous conversation:\n"
                    # Include up to 3 recent exchanges
                    for prev_q, prev_a in self.chat_history[-3:]:
                        history_context += f"User: {prev_q}\nAssistant: {prev_a}\n\n"
                
                # Create enhanced prompt with history and current query
                enhanced_prompt = f"""
                {self.system_message}
                
                {history_context}
                
                User's question: {query}
                
                Provide a helpful, accurate, and concise response addressing the user's question without mentioning sources or citations.
                """
                
                # Call Gemini directly
                try:
                    fallback_llm = ChatGoogleGenerativeAI(
                        model=self.gemini_model,
                        google_api_key=os.getenv("GOOGLE_API_KEY"),
                        temperature=0.7,
                        max_output_tokens=512
                    )
                    
                    answer = fallback_llm.invoke(enhanced_prompt).content
                    
                    if not answer.strip():
                        answer = "I apologize, but I couldn't find enough information to answer your question properly. Could you please rephrase or provide more details?"
                
                except Exception as e:
                    if "quota" in str(e).lower() or "rate" in str(e).lower() or "429" in str(e):
                        answer = "I've hit my API rate limit. Please wait at least 60 seconds before trying again."
                    else:
                        answer = "I apologize for the technical difficulties. Could you try rephrasing your question?"
            
            # Clean up the answer to ensure it's just plain text
            clean_answer = self.format_response(answer)
            self.chat_history.append((query, clean_answer))
            return clean_answer
            
        except Exception as e:
            error_message = str(e)
            
            # Check for specific API errors
            if "quota" in error_message.lower() or "429" in error_message or "rate" in error_message.lower():
                return "I've hit my API rate limit. Please wait at least 60 seconds before trying again."
            elif "not found" in error_message.lower() or "404" in error_message:
                return "Model not found. Please check that you're using the correct model name."
            else:
                # If any error occurs, use direct LLM call as a final fallback
                try:
                    self._rate_limit()
                    fallback_llm = ChatGoogleGenerativeAI(
                        model=self.gemini_model,
                        google_api_key=os.getenv("GOOGLE_API_KEY"),
                        temperature=0.7,
                        max_output_tokens=512
                    )
                    
                    simple_prompt = f"{self.system_message}\n\nUser question: {query}\n\nProvide a helpful response:"
                    answer = fallback_llm.invoke(simple_prompt).content
                    
                    if not answer.strip():
                        answer = "I apologize, but I'm having trouble generating a response. Please try again with a different question."
                    
                    clean_answer = self.format_response(answer)
                    self.chat_history.append((query, clean_answer))
                    return clean_answer
                    
                except Exception as inner_e:
                    return f"Sorry, I encountered an error: {str(inner_e)}"

def main():
    # Load dotenv file if it exists
    load_dotenv()
    
    # API key can be set in .env file or directly in the code
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        api_key = input(f"{Fore.YELLOW}Please enter your Google Gemini API key: {Style.RESET_ALL}")
        os.environ["GOOGLE_API_KEY"] = api_key
    
    print(f"{Fore.CYAN}Community Water Watch Chatbot Setup")
    print(f"{Fore.CYAN}--------------------------------")
    
    chatbot = CommunityWaterWatchChatbot(file_path="content/botdata.txt")
    
    if chatbot.initialize_pipeline():
        chatbot.display_welcome_message()
        while True:
            query = input(f"{Fore.GREEN}You: {Style.RESET_ALL}")
            if query.lower() == "exit":
                print(f"\n{Fore.YELLOW}Thank you for using the {chatbot.bot_name}. Have a great day!")
                break
            response = chatbot.chat(query)
            print(f"\n{chatbot.bot_name}: {response}\n")
    else:
        print(f"{Fore.RED}Failed to initialize chatbot. Please check your configuration and try again.")

if __name__ == "__main__":
    main()