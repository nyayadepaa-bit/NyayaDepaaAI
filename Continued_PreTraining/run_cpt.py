"""
Continued_PreTraining/run_cpt.py
---------------------------------
Continues pretraining LLaMA 3 on your legal corpus using QLoRA.

Usage:
    python run_cpt.py --config cpt_config.yaml

Prerequisites:
    1. Run utils/pdf_extractor.py to extract text from PDFs
    2. Run utils/data_formatter.py to build cpt_train.jsonl & cpt_validation.jsonl
    3. Fill all ### PLACEHOLDERS ### in cpt_config.yaml and .env
"""

import os
import sys
import yaml
import argparse
import logging
from pathlib import Path

import torch
from dotenv import load_dotenv
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    set_seed,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def setup_tokenizer(model_id: str, hf_token: str):
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        token=hf_token,
        trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return tokenizer


def setup_model(cfg: dict, hf_token: str):
    quant_cfg = cfg["quantization"]
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=quant_cfg["load_in_4bit"],
        bnb_4bit_compute_dtype=getattr(torch, quant_cfg["bnb_4bit_compute_dtype"]),
        bnb_4bit_quant_type=quant_cfg["bnb_4bit_quant_type"],
        bnb_4bit_use_double_quant=quant_cfg["bnb_4bit_use_double_quant"],
    )

    model = AutoModelForCausalLM.from_pretrained(
        cfg["model"]["base_model_id"],
        quantization_config=bnb_config,
        torch_dtype=getattr(torch, cfg["model"]["torch_dtype"]),
        device_map="auto",
        token=hf_token,
        trust_remote_code=cfg["model"]["trust_remote_code"],
        attn_implementation="flash_attention_2" if cfg["model"]["use_flash_attention"] else "eager",
    )

    model = prepare_model_for_kbit_training(model)

    lora_cfg = cfg["lora"]
    lora_config = LoraConfig(
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["lora_alpha"],
        target_modules=lora_cfg["target_modules"],
        lora_dropout=lora_cfg["lora_dropout"],
        bias=lora_cfg["bias"],
        task_type=lora_cfg["task_type"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model


def main():
    parser = argparse.ArgumentParser(description="Continued PreTraining for LegalLlama3")
    parser.add_argument("--config", type=str, default="cpt_config.yaml")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)

    cfg = load_config(args.config)
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN not set in .env file. ### ADD YOUR HUGGINGFACE TOKEN ###")

    # Load datasets
    logger.info("Loading datasets...")
    data_cfg = cfg["data"]
    dataset = load_dataset(
        "json",
        data_files={
            "train": data_cfg["train_file"],
            "validation": data_cfg["val_file"],
        },
        num_proc=data_cfg["dataset_num_proc"],
    )
    logger.info(f"Train: {len(dataset['train'])} | Val: {len(dataset['validation'])}")

    # Setup tokenizer and model
    logger.info("Loading tokenizer...")
    tokenizer = setup_tokenizer(cfg["model"]["base_model_id"], hf_token)

    logger.info("Loading model with QLoRA...")
    model = setup_model(cfg, hf_token)

    # Training arguments
    train_cfg = cfg["training"]
    training_args = TrainingArguments(
        output_dir=train_cfg["output_dir"],
        num_train_epochs=train_cfg["num_train_epochs"],
        per_device_train_batch_size=train_cfg["per_device_train_batch_size"],
        per_device_eval_batch_size=train_cfg["per_device_eval_batch_size"],
        gradient_accumulation_steps=train_cfg["gradient_accumulation_steps"],
        learning_rate=train_cfg["learning_rate"],
        lr_scheduler_type=train_cfg["lr_scheduler_type"],
        warmup_ratio=train_cfg["warmup_ratio"],
        weight_decay=train_cfg["weight_decay"],
        fp16=train_cfg["fp16"],
        bf16=train_cfg["bf16"],
        logging_steps=train_cfg["logging_steps"],
        eval_steps=train_cfg["eval_steps"],
        save_steps=train_cfg["save_steps"],
        save_total_limit=train_cfg["save_total_limit"],
        evaluation_strategy=train_cfg["evaluation_strategy"],
        load_best_model_at_end=train_cfg["load_best_model_at_end"],
        metric_for_best_model=train_cfg["metric_for_best_model"],
        report_to=train_cfg["report_to"],
        run_name=train_cfg["run_name"],
        dataloader_num_workers=4,
        group_by_length=True,
        ddp_find_unused_parameters=False,
    )

    # SFT Trainer (used even for CPT — it handles packing efficiently)
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        tokenizer=tokenizer,
        max_seq_length=data_cfg["max_seq_length"],
        packing=cfg.get("packing", True),
        dataset_text_field="text",
    )

    logger.info("Starting Continued PreTraining...")
    trainer.train()

    logger.info(f"Saving model to {train_cfg['output_dir']}")
    trainer.save_model(train_cfg["output_dir"])
    tokenizer.save_pretrained(train_cfg["output_dir"])

    logger.info("CPT Complete! Model saved.")


if __name__ == "__main__":
    main()
