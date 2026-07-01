"""
LoRA fine-tuning script for continuous learning.

Usage (when enough conversation data collected):
    python -m learning.finetune --base-model models_cache/Llama-3.1-8B-Instruct-Q4_K_M.gguf

Requires extra deps:
    pip install unsloth transformers datasets peft trl accelerate bitsandbytes
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description="LoRA fine-tune from conversation logs")
    parser.add_argument("--data", default="data/finetune/training.jsonl")
    parser.add_argument("--base-model", required=True, help="Path to base GGUF model")
    parser.add_argument("--output-dir", default="models_cache/adapters")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    args = parser.parse_args()

    print("=" * 60)
    print("Fine-tuning Preparation")
    print("=" * 60)
    print(f"  Data:      {args.data}")
    print(f"  Base:      {args.base_model}")
    print(f"  Output:    {args.output_dir}")
    print(f"  Epochs:    {args.epochs}")
    print(f"  LR:        {args.lr}")
    print()
    print("To run actual fine-tuning, install unsloth:")
    print("  pip install unsloth transformers datasets peft trl accelerate bitsandbytes")
    print()
    print("Then implement the training loop using unsloth's FastLanguageModel:")
    print("  https://github.com/unslothai/unsloth")
    print()
    print("Example training snippet:")
    print("""
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=2048,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=16, target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    )
    dataset = load_dataset("json", data_files=args.data, split="train")
    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer,
        train_dataset=dataset,
        args=TrainingArguments(
            output_dir=args.output_dir,
            per_device_train_batch_size=2,
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            save_strategy="epoch",
        ),
    )
    trainer.train()
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"LoRA adapters saved to {args.output_dir}")
    """)


if __name__ == "__main__":
    main()
