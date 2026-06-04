"""LLM configuration panel for managing AI model providers."""

import json
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.agents.llm import BaseLLMProvider, LLMConfig
from src.agents.llm.factory import ProviderFactory
from src.agents.llm.registry import ProviderRegistry


class LLMConfigPanel(QWidget):
    """Panel for configuring LLM providers.
    
    This panel allows users to configure different LLM providers
    (Ollama, OpenAI, Anthropic, etc.) and test connections.
    
    Signals:
        config_changed: Emitted when configuration changes.
        provider_created: Emitted when a new provider is created.
    """
    
    config_changed = Signal(LLMConfig)
    provider_created = Signal(BaseLLMProvider)
    
    SETTINGS_FILE = Path("settings.json")

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the LLM configuration panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self.logger = logging.getLogger(f"{__name__}.LLMConfigPanel")
        self.current_provider: Optional[BaseLLMProvider] = None

        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>LLM Configuration</h2>")
        layout.addWidget(title)
        
        # Provider selection
        provider_group = QGroupBox("Provider")
        provider_layout = QFormLayout(provider_group)

        self.provider_combo = QComboBox()
        # Get available providers from registry
        available_providers = ProviderRegistry.list_providers()
        # Format provider names for display (capitalize first letter)
        display_providers = [p.capitalize() for p in available_providers]
        self.provider_combo.addItems(display_providers)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addRow("Provider:", self.provider_combo)

        layout.addWidget(provider_group)
        
        # Connection settings
        connection_group = QGroupBox("Connection")
        connection_layout = QFormLayout(connection_group)
        
        self.base_url_input = QLineEdit("http://localhost:11434")
        connection_layout.addRow("Base URL:", self.base_url_input)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Not required for Ollama")
        self.api_key_input.setEnabled(False)
        connection_layout.addRow("API Key:", self.api_key_input)
        
        layout.addWidget(connection_group)
        
        # Model settings
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout(model_group)
        
        self.model_input = QLineEdit("qwen3-vl:8b")
        model_layout.addRow("Model:", self.model_input)
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        model_layout.addRow("Temperature:", self.temperature_spin)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 100000)
        self.max_tokens_spin.setValue(4096)  # Increased for longer documents
        model_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.1)
        self.top_p_spin.setValue(1.0)
        model_layout.addRow("Top P:", self.top_p_spin)

        self.check_interval_spin = QSpinBox()
        self.check_interval_spin.setRange(5, 3600)
        self.check_interval_spin.setSingleStep(5)
        self.check_interval_spin.setValue(10)
        self.check_interval_spin.setSuffix(" s")
        model_layout.addRow("Check Interval:", self.check_interval_spin)

        layout.addWidget(model_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self._on_test_connection)
        button_layout.addWidget(self.test_button)
        
        self.apply_button = QPushButton("Apply Configuration")
        self.apply_button.clicked.connect(self._on_apply_config)
        button_layout.addWidget(self.apply_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def _load_config(self) -> None:
        """Populate UI fields from settings.json if it exists."""
        if not self.SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(self.SETTINGS_FILE.read_text(encoding="utf-8"))
            llm = data.get("llm", {})

            if provider := llm.get("provider"):
                # Find the matching combo entry (stored lowercase, displayed capitalised)
                index = self.provider_combo.findText(
                    provider.capitalize(), Qt.MatchFlag.MatchFixedString
                )
                if index >= 0:
                    self.provider_combo.setCurrentIndex(index)

            if model := llm.get("model"):
                self.model_input.setText(model)
            if base_url := llm.get("base_url"):
                self.base_url_input.setText(base_url)
            if (temp := llm.get("temperature")) is not None:
                self.temperature_spin.setValue(float(temp))
            if (max_tok := llm.get("max_tokens")) is not None:
                self.max_tokens_spin.setValue(int(max_tok))
            if (top_p := llm.get("top_p")) is not None:
                self.top_p_spin.setValue(float(top_p))
            if (interval := llm.get("check_interval")) is not None:
                self.check_interval_spin.setValue(int(interval))

            self.logger.info("LLM configuration loaded from settings.json")
        except Exception as exc:
            self.logger.warning(f"Could not load settings.json: {exc}")

    def _save_config(self) -> None:
        """Persist the current UI fields to settings.json (api_key excluded)."""
        config = self._get_current_config()
        data: dict = {}
        if self.SETTINGS_FILE.exists():
            try:
                data = json.loads(self.SETTINGS_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self.logger.warning(f"Ignoring corrupt settings.json — will overwrite: {exc}")

        data["llm"] = {
            "provider": config.provider,
            "model": config.model,
            "base_url": config.base_url,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "check_interval": self.check_interval_spin.value(),
        }
        try:
            self.SETTINGS_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            self.logger.info("LLM configuration saved to settings.json")
        except Exception as exc:
            self.logger.warning(f"Could not save settings.json: {exc}")

    def _get_current_config(self) -> LLMConfig:
        """Get the current configuration from UI inputs.

        Returns:
            LLMConfig object with current settings.
        """
        # Get provider name from combo (lowercase for internal use)
        provider_name = self.provider_combo.currentText().lower()

        return LLMConfig(
            provider=provider_name,
            model=self.model_input.text(),
            temperature=self.temperature_spin.value(),
            max_tokens=self.max_tokens_spin.value(),
            top_p=self.top_p_spin.value(),
            base_url=self.base_url_input.text() or None,
            api_key=self.api_key_input.text() or None,
        )

    @Slot(str)
    def _on_provider_changed(self, provider: str) -> None:
        """Handle provider selection change.

        Args:
            provider: Selected provider name.
        """
        self.logger.info(f"Provider changed to: {provider}")

        # Enable/disable API key based on provider
        provider_lower = provider.lower()
        if provider_lower == "ollama":
            self.api_key_input.setEnabled(False)
            self.api_key_input.setPlaceholderText("Not required for Ollama")
            self.base_url_input.setText("http://localhost:11434")
            self.model_input.setText("qwen3-vl:8b")
        elif provider_lower == "openai":
            self.api_key_input.setEnabled(True)
            self.api_key_input.setPlaceholderText("Enter OpenAI API key")
            self.base_url_input.setText("")
            self.model_input.setText("gpt-4o-mini")
        else:
            self.api_key_input.setEnabled(True)
            self.api_key_input.setPlaceholderText("Enter API key")
            self.base_url_input.setText("")
            self.model_input.setText("")

    @Slot()
    def _on_test_connection(self) -> None:
        """Handle test connection button click."""
        self.logger.info("Testing connection...")
        self.status_label.setText("Testing connection...")
        self.status_label.setStyleSheet("color: orange;")

        async def test_async():
            try:
                config = self._get_current_config()
                provider = ProviderFactory.create(config)

                # Test connection
                is_available = await provider.is_available()

                if is_available:
                    self.status_label.setText("Connection successful!")
                    self.status_label.setStyleSheet("color: green;")
                    self.logger.info("Connection test successful")
                else:
                    self.status_label.setText("Connection failed: Provider not available")
                    self.status_label.setStyleSheet("color: red;")
                    self.logger.error("Connection test failed: Provider not available")

            except Exception as e:
                self.status_label.setText(f"Connection failed: {str(e)}")
                self.status_label.setStyleSheet("color: red;")
                self.logger.error(f"Connection test failed: {e}")

        # Run the async test
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_async())

    @Slot()
    def _on_apply_config(self) -> None:
        """Handle apply configuration button click."""
        self.logger.info("Applying configuration...")

        try:
            config = self._get_current_config()

            # Create provider using ProviderFactory
            self.current_provider = ProviderFactory.create(config)

            # Persist before emitting so the saved state is always consistent
            self._save_config()

            # Emit signals
            self.config_changed.emit(config)
            self.provider_created.emit(self.current_provider)

            self.status_label.setText("Configuration applied successfully!")
            self.status_label.setStyleSheet("color: green;")
            self.logger.info("Configuration applied")

        except Exception as e:
            self.status_label.setText(f"Failed to apply configuration: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
            self.logger.error(f"Failed to apply configuration: {e}")

    def get_current_provider(self) -> Optional[BaseLLMProvider]:
        """Get the currently configured provider.

        Returns:
            Current LLM provider or None if not configured.
        """
        return self.current_provider

    def get_check_interval(self) -> int:
        """Return the configured producer check interval in seconds."""
        return self.check_interval_spin.value()

    def apply_default_config(self) -> None:
        """Apply the default configuration automatically on startup.

        This should be called by MainWindow after agents are created and signals are connected.
        """
        self.logger.info("Auto-applying default LLM configuration...")

        try:
            # Get the default configuration from UI
            config = self._get_current_config()

            # Create provider using ProviderFactory
            self.current_provider = ProviderFactory.create(config)

            # Emit signals to distribute provider to agents
            self.config_changed.emit(config)
            self.provider_created.emit(self.current_provider)

            self.status_label.setText("Default configuration applied automatically")
            self.status_label.setStyleSheet("color: green;")
            self.logger.info("Default configuration applied successfully")

        except Exception as e:
            self.status_label.setText(f"Auto-config failed: {str(e)}")
            self.status_label.setStyleSheet("color: orange;")
            self.logger.error(f"Failed to auto-apply configuration: {e}")

