"""
Supervised_FineTuning/run_sft_explanation.py
---------------------------------------------
Fine-tunes the model on Prediction + Explanation task.
The model learns to predict the judgment AND generate a detailed legal explanation.

Usage:
    python run_sft_explanation.py --config sft_config.yaml
"""

import os
import yaml
import argparse
import logging

import torch
from dotenv import load_dotenv
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments, set_seed
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path):
    with open(config_path) as f:
        return yaml.safe_load(f)


def build_model_and_tokenizer(cfg, hf_token):
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
        model_id, quantization_config=bnb_config,
        torch_dtype=getattr(torch, cfg["model"]["torch_dtype"]),
        device_map="auto", token=hf_token, trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    lc = cfg["lora"]
    model = get_peft_model(model, LoraConfig(
        r=lc["r"], lora_alpha=lc["lora_alpha"], target_modules=lc["target_modules"],
        lora_dropout=lc["lora_dropout"], bias=lc["bias"], task_type=lc["task_type"],
    ))
    model.print_trainable_parameters()
    return model, tokenizer


def main():
    parser = argparse.ArgumentParser(description="SFT: Prediction + Explanation")
    parser.add_argument("--config", type=str, default="sft_config.yaml")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    cfg = load_config(args.config)
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN not found. ### ADD YOUR HUGGINGFACE TOKEN TO .env ###")

    data_cfg  = cfg["data"]
    train_cfg = cfg["training"]

    logger.info("Loading explanation dataset...")
    dataset = load_dataset(
        "json",
        data_files={"train": data_cfg["explanation_train"], "validation": data_cfg["explanation_val"]},
        num_proc=data_cfg["dataset_num_proc"],
    )
    logger.info(f"Train: {len(dataset['train'])} | Val: {len(dataset['validation'])}")

    model, tokenizer = build_model_and_tokenizer(cfg, hf_token)
    output_dir = train_cfg["explanation_output_dir"]

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
        bf16=train_cfg["bf16"], fp16=train_cfg["fp16"],
        logging_steps=train_cfg["logging_steps"],
        eval_steps=train_cfg["eval_steps"],
        save_steps=train_cfg["save_steps"],
        save_total_limit=train_cfg["save_total_limit"],
        evaluation_strategy=train_cfg["evaluation_strategy"],
        load_best_model_at_end=train_cfg["load_best_model_at_end"],
        metric_for_best_model=train_cfg["metric_for_best_model"],
        report_to=train_cfg["report_to"],
        run_name="legal-llama3-sft-explanation",
    )

    trainer = SFTTrainer(
        model=model, args=training_args,
        train_dataset=dataset["train"], eval_dataset=dataset["validation"],
        tokenizer=tokenizer,
        max_seq_length=data_cfg["max_seq_length"],
        dataset_text_field="text",
        packing=False,
    )

    logger.info("Starting SFT — Prediction + Explanation Task...")
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"SFT Explanation complete! Model saved to {output_dir}")


if __name__ == "__main__":
    main()
