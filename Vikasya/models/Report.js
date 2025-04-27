const mongoose = require("mongoose");

const reportSchema = new mongoose.Schema({
  id: { type: String, required: true, unique: true },
  type: { type: String, required: true }, // e.g., "contamination"
  title: { type: String, required: true }, // e.g., "Bellandur Lake - Foam Formation"
  description: { type: String, required: true },
  location: {
    lat: { type: Number, required: true },
    lng: { type: Number, required: true },
  },
  status: { 
    type: String, 
    required: true, 
    enum: ["reported", "investigating", "resolved"], 
    default: "reported" 
  },
  reportedAt: { type: Date, default: Date.now },
  reporter: { type: String, required: true }, // e.g., "Environmental Watchdog"
  quality: {
    ph: { type: Number },
    turbidity: { type: Number },
    contaminants: [{ type: String }], // e.g., ["Detergents", "Industrial Waste"]
  },
  trend: [{ type: Number }], // e.g., [80, 75, 70, 65, 60, 55, 50]
  mediaUrl: { type: String }, // Optional media file path
  userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  emailStatus: { type: String, default: "Pending" },
  emailRecipients: [{ type: String }],
});

module.exports = mongoose.model("Report", reportSchema);