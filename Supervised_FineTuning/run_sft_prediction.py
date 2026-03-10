"""
Supervised_FineTuning/run_sft_prediction.py
--------------------------------------------
Fine-tunes the CPT model on legal judgment prediction (Allowed / Dismissed / Partially Allowed).

Usage:
    python run_sft_prediction.py --config sft_config.yaml

Prerequisites:
    1. CPT phase must be complete (or use base LLaMA 3)
    2. Labeled prediction dataset must exist (sft_prediction_train.jsonl)
"""

import os
import sys
import yaml
import argparse
import logging

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
from trl import SFTTrainer

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RESPONSE_TEMPLATE = "<|start_header_id|>assistant<|end_header_id|>"


def load_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def build_model_and_tokenizer(cfg: dict, hf_token: str):
    model_id = cfg["model"]["base_model_id"]

    tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=cfg["quantization"]["load_in_4bit"],
        bnb_4bit_compute_dtype=getattr(torch, cfg["quantization"]["bnb_4bit_compute_dtype"]),
        bnb_4bit_quant_type=cfg["quantization"]["bnb_4bit_quant_type"],
        bnb_4bit_use_double_quant=cfg["quantization"]["bnb_4bit_use_double_quant"],
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        torch_dtype=getattr(torch, cfg["model"]["torch_dtype"]),
        device_map="auto",
        token=hf_token,
        trust_remote_code=cfg["model"]["trust_remote_code"],
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

    return model, tokenizer


def main():
    parser = argparse.ArgumentParser(description="SFT: Judgment Prediction")
    parser.add_argument("--config", type=str, default="sft_config.yaml")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    cfg = load_config(args.config)
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN not set. ### ADD YOUR HUGGINGFACE TOKEN TO .env ###")

    data_cfg  = cfg["data"]
    train_cfg = cfg["training"]

    logger.info("Loading prediction dataset...")
    dataset = load_dataset(
        "json",
        data_files={
            "train": data_cfg["prediction_train"],
            "validation": data_cfg["prediction_val"],
        },
        num_proc=data_cfg["dataset_num_proc"],
    )
    logger.info(f"Train: {len(dataset['train'])} | Val: {len(dataset['validation'])}")

    model, tokenizer = build_model_and_tokenizer(cfg, hf_token)

    output_dir = train_cfg["prediction_output_dir"]
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=train_cfg["num_train_epochs"],
        per_device_train_batch_size=train_cfg["per_device_train_batch_size"],
        per_device_eval_batch_size=train_cfg["per_device_eval_batch_size"],
        gradient_accumulation_steps=train_cfg["gradient_accumulation_steps"],
        learning_rate=train_cfg["learning_rate"],
        lr_scheduler_type=train_cfg["lr_scheduler_type"],
        warmup_ratio=train_cfg["warmup_ratio"],
        weight_decay=train_cfg["weight_decay"],
        bf16=train_cfg["bf16"],
        fp16=train_cfg["fp16"],
        logging_steps=train_cfg["logging_steps"],
        eval_steps=train_cfg["eval_steps"],
        save_steps=train_cfg["save_steps"],
        save_total_limit=train_cfg["save_total_limit"],
        evaluation_strategy=train_cfg["evaluation_strategy"],
        load_best_model_at_end=train_cfg["load_best_model_at_end"],
        metric_for_best_model=train_cfg["metric_for_best_model"],
        report_to=train_cfg["report_to"],
        run_name="legal-llama3-sft-prediction",
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        tokenizer=tokenizer,
        max_seq_length=data_cfg["max_seq_length"],
        dataset_text_field="text",
        packing=False,
    )

    logger.info("Starting SFT — Prediction Task...")
    trainer.train()

    logger.info(f"Saving model to {output_dir}")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info("SFT Prediction complete!")


if __name__ == "__main__":
    main()
