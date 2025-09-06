import json
import re
from collections import defaultdict
from typing import List, Dict
from src.services.llm_service import get_gemini_model, get_lmstudio_response, get_openai_model
from src.utils.helpers import is_general_query, format_history_text
from src.utils.get_customer_info import get_customer_store_info
from sqlalchemy.orm import Session

def generate_llm_response(
    user_query: str,
    search_results: list,
    history: list = None,
    include_specs: bool = False,
    model_choice: str = "gemini",
    needs_product_search: bool = True,
    wants_images: bool = False,
    is_image_search: bool = False,
    db: Session = None,
    customer_id: str = None,
    api_key: str = None,
    is_sale: bool = False
) -> str:
    """
    Tạo prompt và gọi đến LLM để sinh câu trả lời.
    """
    if is_general_query(user_query):
        if not search_results:
            return {"answer": "Dạ, cửa hàng em chưa có sản phẩm nào để giới thiệu ạ.", "product_images": []} if wants_images else "Dạ, cửa hàng em chưa có sản phẩm nào để giới thiệu ạ."
        product_names = [item.get('product_name', 'N/A') for item in search_results]
        answer = (
            "Hiện tại cửa hàng em đang kinh doanh nhiều loại sản phẩm về các thiết bị điện tử, ví dụ như: "
            + ".\n".join(product_names) + " và nhiều sản phẩm khác nữa"
            + ".\n\nAnh/chị muốn tìm hiểu thêm về sản phẩm nào không ạ?"
        )
        return {"answer": answer, "product_images": []} if wants_images else answer

    context = ""
    has_history = bool(history)
    if has_history:
        context += f"Lịch sử hội thoại gần đây:\n{format_history_text(history)}\n"
    else:
        context += "Lịch sử hội thoại gần đây:\n(Đây là tin nhắn đầu tiên)\n"

    if needs_product_search:
        context += _build_product_context(search_results, include_specs, is_sale)

    product_infos = [
        f"{p.get('product_name', '')} ({p.get('properties', '')})"
        for p in search_results if p.get('product_name')
    ] if wants_images else []

    store_info_dict = None
    if db and customer_id:
        store_info_dict = get_customer_store_info(db, customer_id)

    prompt = _build_prompt(user_query, context, needs_product_search, wants_images, product_infos, has_history, is_image_search, store_info_dict)

    print("--- PROMPT GỬI ĐẾN LLM ---")
    print(prompt)
    print("--------------------------")

    llm_response = None
    try:
        if model_choice == "gemini":
            model = get_gemini_model(api_key=api_key)
            if model:
                response = model.generate_content(prompt, safety_settings={'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE'})
                llm_response = response.text.strip()
        elif model_choice == "lmstudio":
            llm_response = get_lmstudio_response(prompt)
        elif model_choice == "openai":
            openai = get_openai_model(api_key=api_key)
            if not openai:
                return {"answer": "Không tìm thấy OpenAI API key.", "product_images": []} if wants_images else "Không tìm thấy OpenAI API key."
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=4000
            )
            llm_response = response.choices[0].message.content.strip()
            usage = response.usage
            print(f"📊 Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}")
            cost = (usage.prompt_tokens * 0.15 + usage.completion_tokens * 0.6) / 1_000_000
            print(f"💰 Estimated cost (GPT-4o-mini): ${cost:.6f}")

    except Exception as e:
        print(f"Lỗi khi gọi LLM: {e}")
        llm_response = None

    if wants_images:
        answer, product_images = _parse_answer_and_images(llm_response, product_infos)
        return {"answer": answer, "product_images": product_images}
    else:
        if llm_response:
            return llm_response
        return _get_fallback_response(search_results, needs_product_search)


def _build_product_context(search_results: List[Dict], include_specs: bool = False, is_sale: bool = False) -> str:
    """
    Xây dựng context thông tin sản phẩm, nhóm các sản phẩm cùng tên lại với nhau.
    """
    product_groups = defaultdict(list)
    
    for item in search_results:
        product_groups[item.get('product_name', 'N/A')].append(item)

    product_context = "Dữ liệu sản phẩm tìm thấy:\n"
    
    for name, items in product_groups.items():
        product_context += f"- Tên: {name}\n"

        sorted_items = sorted(items, key=lambda x: str(x.get('properties', '')))

        if len(sorted_items) == 1:
            item = sorted_items[0]
            prop = item.get('properties')
            if prop and str(prop).strip() != '0':
                product_context += f"  Thuộc tính: {prop}\n"
            
            price = item.get('lifecare_price', 0)
            price_str = f"{price:,.0f}đ" if price is not None and price > 0 else "Liên hệ"
            sale_price = item.get('sale_price', 0)
            sale_price_str = f" - Giá buôn: {sale_price:,.0f}đ" if is_sale and sale_price is not None and sale_price > 0 else ""
            product_context += f"  Giá: {price_str}{sale_price_str}\n"
            inventory = item.get('inventory', 0)
            if inventory > 0:
                product_context += f"  Tình trạng: Còn hàng ({inventory} sản phẩm)\n"
            else:
                product_context += "  Tình trạng: Hết hàng\n"
            guarantee = item.get('guarantee')
            product_context += f"  Bảo hành: {guarantee}\n"
            link_product = item.get('link_product')
            product_context += f"  Link sản phẩm: {link_product}\n"
        else:
            product_context += "  Lưu ý: Sản phẩm này có nhiều thuộc tính khác nhau (ví dụ: loại, cỡ, model, màu,...). Các phiên bản có sẵn:\n"
            for item in sorted_items:
                prop = item.get('properties', 'N/A')
                price = item.get('lifecare_price', 0)
                sale_price = item.get('sale_price', 0)
                inventory = item.get('inventory', 0)
                price_str = f"{price:,.0f}đ" if price is not None and price > 0 else "Liên hệ"
                sale_price_str = f" - Giá buôn: {sale_price:,.0f}đ" if is_sale and sale_price is not None and sale_price > 0 else ""
                stock_str = f"Còn hàng ({inventory})" if inventory > 0 else "Hết hàng"
                guarantee = item.get('guarantee')
                link_product = item.get('link_product')
                product_context += f"    + {prop} - Giá: {price_str}{sale_price_str} - Tình trạng: {stock_str} - Bảo hành: {guarantee} - Link sản phẩm: {link_product}\n"
        
        if include_specs:
            product_context += f"  Mô tả: {sorted_items[0].get('specifications', 'N/A')}\n"
    return product_context


def _build_prompt(user_query: str, context: str, needs_product_search: bool, wants_images: bool = False, product_infos: list = None, has_history: bool = None, is_image_search: bool = False, store_info_dict: dict = None) -> str:
    """
    Xây dựng prompt cho LLM với các quy tắc hội thoại nâng cao.
    """
    image_instruction = ""
    if wants_images:
        product_list_str = '\n'.join(f'- {info}' for info in product_infos or [])
        image_instruction = f"""## HƯỚNG DẪN ĐẶC BIỆT KHI CUNG CẤP HÌNH ẢNH ##
- Nhiệm vụ của bạn là tạo ra một danh sách các sản phẩm kèm ảnh dựa trên "DỮ LIỆU CUNG CẤP".
- **KHÔNG** được hỏi lại khách hàng. **KHÔNG** thêm bất kỳ lời thoại nào khác.
- Câu trả lời của bạn **BẮT BUỘC** phải có 2 phần: `[ANSWER]` và `[PRODUCT_IMAGE]`.

- **Phần [ANSWER]:**
    - **KHÔNG** thêm bất kỳ lời chào hay câu giới thiệu nào.
    - **Chỉ liệt kê** lại các sản phẩm mà khách muốn xem ảnh.
    - **Mỗi sản phẩm phải nằm trên một dòng riêng**, **không được** cách dòng quá 1 dòng, bắt đầu bằng dấu gạch ngang (-).
    - Ghi rõ Tên và Giá của sản phẩm.
    - **VÍ DỤ ĐỊNH DẠNG PHẦN ANSWER:**
        - Máy hàn OSSTEAM T210 - giá 145,000đ
        - Máy hàn MECHANIC A210 - giá 780,000đ

- **Phần [PRODUCT_IMAGE]:**
    - Liệt kê CHÍNH XÁC tên định danh (có dạng Tên (Thuộc tính)) của các sản phẩm đã liệt kê trong phần [ANSWER].
    - **Mỗi tên một dòng và phải theo đúng thứ tự** đã liệt kê ở phần [ANSWER].

- **QUY TẮC CHỌN ẢNH:** Phải đối chiếu chính xác từng chi tiết trong câu hỏi của khách (bao gồm cả model, thuộc tính) với "Danh sách sản phẩm". Chỉ chọn những dòng khớp **chính xác 100%**.

- Danh sách sản phẩm có thể dùng cho [PRODUCT_IMAGE]:
{product_list_str}
"""

    store_info = ""
    if store_info_dict:
        parts = []
        if store_info_dict.get("store_name"):
            parts.append(f"- Tên cửa hàng: {store_info_dict['store_name']}")
        if store_info_dict.get("store_address"):
            parts.append(f"- Địa chỉ: {store_info_dict['store_address']}")
        if store_info_dict.get("store_phone"):
            parts.append(f"- Hotline: {store_info_dict['store_phone']}")
        if store_info_dict.get("info_more"):
            parts.append(f"- Thông tin thêm: {store_info_dict['info_more']}")
        store_info = "\n".join(parts)

    greeting_rule = ""
    
    if not wants_images:
        if not has_history:
            greeting_rule = '- **Chào hỏi:** Bắt đầu câu trả lời bằng lời chào đầy đủ "Dạ, em chào anh/chị ạ." vì đây là tin nhắn đầu tiên.'
        else:
            greeting_rule = '- **Chào hỏi:** KHÔNG chào hỏi đầy đủ. Bắt đầu câu trả lời trực tiếp bằng "Dạ,".'

    image_search_priority_rule = ""
    if is_image_search:
        image_search_priority_rule = """
**QUY TẮC ƯU TIÊN TUYỆT ĐỐI (TÌM KIẾM BẰNG HÌNH ẢNH):**
- Cuộc trò chuyện này bắt đầu bằng việc khách hàng gửi một hình ảnh để tìm kiếm.
- Nhiệm vụ của bạn là trả lời câu hỏi của khách hàng DỰA HOÀN TOÀN vào "DỮ LIỆU SẢN PHẨM TÌM THẤY".
- **TUYỆT ĐỐI BỎ QUA** lịch sử trò chuyện cũ và không được liệt kê các sản phẩm khác không có trong dữ liệu tìm thấy.
"""

    if not needs_product_search:
        return f"""## BỐI CẢNH ##
- Bạn là một nhân viên tư vấn chuyên nghiệp của cửa hàng.
- Thông tin cố định về cửa hàng:
{store_info}
- Dưới đây là lịch sử trò chuyện.

## NHIỆM VỤ (RẤT QUAN TRỌNG) ##
- Trả lời câu hỏi của sau khách hàng: "{user_query}"
- **BẠN PHẢI TRẢ LỜI DỰA TRÊN NGỮ CẢNH CỦA LỊCH SỬ HỘI THOẠI.**
- **TUYỆT ĐỐI KHÔNG ĐƯỢC THAY ĐỔI CHỦ ĐỀ.** Ví dụ: nếu cuộc trò chuyện đang về "sản phẩm A", câu trả lời của bạn cũng phải về "sản phẩm A", không được tự ý chuyển sang "sản phẩm B".
- Hãy trả lời một cách thân thiện và lễ phép.
- **Nếu tin nhắn cuối cùng trong lịch sử là bot nói về việc chuyển cho nhân viên, và câu hỏi mới của khách là một lời chào chung chung (ví dụ: "Hi", "hello", "chào shop"), HÃY bỏ qua ngữ cảnh cũ và chào lại một cách bình thường như một cuộc trò chuyện mới.** Ví dụ: "Dạ, em chào anh/chị. Em có thể giúp gì cho mình ạ?"

## QUY TẮC ##

1.  {greeting_rule}

2. Nếu khách hàng hỏi những từ hoặc câu bạn không hiểu hãy nói: "Dạ em chưa hiểu ý của anh/chị ạ."

3. Thông tin nào về cửa hàng chưa được cung cấp thì **TUYỆT ĐỐI KHÔNG** được trả lời theo ý bạn. Hãy nói rằng: "Dạ, em chưa có thông tin về 'tên_thông_tin_khách_hỏi' ạ."

## DỮ LIỆU CUNG CẤP ##
{context}

## CÂU TRẢ LỜI CỦA BẠN: ##
"""

    return f"""## BỐI CẢNH ##
- Bạn là một nhân viên tư vấn chuyên nghiệp, thông minh và khéo léo.
- **Thông tin cố định về cửa hàng (luôn ghi nhớ và sử dụng khi cần):**
{store_info}

## NHIỆM VỤ ##
- Phân tích ngữ cảnh và câu hỏi của khách hàng để trả lời một cách chính xác và tự nhiên như người thật.
- **Ưu tiên hàng đầu: Luôn trả lời trực tiếp vào câu hỏi của khách hàng trước, sau đó mới áp dụng các quy tắc khác.**
- Thông tin nào về cửa hàng chưa được cung cấp thì **TUYỆT ĐỐI KHÔNG** được trả lời theo ý bạn. Hãy nói rằng: "Dạ, em chưa có thông tin về 'tên_thông_tin_khách_hỏi' ạ."
- TUYỆT ĐỐI chỉ sử dụng thông tin trong phần "DỮ LIỆU CUNG CẤP".

- **Câu hỏi của khách hàng**: "{user_query}"

## DỮ LIỆU CUNG CẤP ##
- Dưới đây là lịch sử trò chuyện và dữ liệu về các sản phẩm liên quan.
{context}

{image_instruction}

## QUY TẮC HỘI THOẠI BẮT BUỘC ##

1.  {image_search_priority_rule}

2.  {greeting_rule}

3.  **Lọc và giữ vững chủ đề (QUAN TRỌNG NHẤT):**
    - Dựa vào lịch sử hội thoại, Phải xác định **chủ đề chính** của cuộc trò chuyện (ví dụ: "máy hàn", "kính hiển vi RELIFE").
    - **TUYỆT ĐỐI KHÔNG** giới thiệu sản phẩm không thuộc chủ đề chính.
    - Nếu khách hỏi một sản phẩm không có trong dữ liệu cung cấp, hãy trả lời rằng: "Dạ, bên em không bán 'tên_sản_phẩm_khách_hỏi' ạ."

4.  **Sản phẩm có nhiều model, combo, cỡ, màu sắc,... (tùy thuộc tính):**
    - Khi giới thiệu lần đầu, chỉ nói tên sản phẩm chính và hãy thông báo có nhiều màu hoặc có nhiều model hoặc có nhiều cỡ,... (tùy vào thuộc tính của sản phẩm).
    - **Khi khách hỏi trực tiếp về số lượng** (ví dụ: "chỉ có 3 màu thôi à?"), bạn phải trả lời thẳng vào câu hỏi.

5.  **Xử lý câu hỏi chung về danh mục:**
    - Nếu khách hỏi "shop có bán máy hàn không?, có kính hiển vi không?", **KHÔNG liệt kê sản phẩm ra ngay**. Hãy xác nhận là có bán và có thể nói ra một số đặc điểm riêng biệt như thương hiệu, hãng có trong dữ liệu cung cấp và hỏi lại để làm rõ nhu cầu lựa chọn.

6.  **Liệt kê sản phẩm:**
    - Khi khách hàng yêu cầu liệt kê các sản phẩm (ví dụ: "có những loại nào", "kể hết ra đi"), bạn **PHẢI** trình bày câu trả lời dưới dạng một danh sách rõ ràng.
    - **Mỗi sản phẩm phải nằm trên một dòng riêng**, bắt đầu bằng dấu gạch ngang (-).
    - **KHÔNG** được gộp tất cả các tên sản phẩm vào trong một đoạn văn.
    - Hãy liệt kê sản phẩm mà theo bạn có độ liên quan cao nhất đến câu hỏi của khách hàng trước.

7.  **Xem thêm / Loại khác:**
    - Áp dụng khi khách hỏi "còn không?", "còn loại nào nữa không?" hoặc có thể là "tiếp đi" (tùy vào ngữ cảnh cuộc trò chuyện). Hiểu rằng khách muốn xem thêm sản phẩm khác (cùng chủ đề), **không phải hỏi tồn kho**.

8.  **Tồn kho:**
    - **KHÔNG** liệt kê các sản phẩm hoặc các phiên bản sản phẩm có "Tình trạng: Hết hàng".
    - **KHÔNG** tự động nói ra số lượng tồn kho chính xác hay tình trạng "Còn hàng". Chỉ nói khi khách hỏi.
    
9.  **Giá sản phẩm:**
    - **Các sản phẩm có giá là **Liên hệ** thì **KHÔNG ĐƯỢC** nói ra giá, chỉ nói tên sản phẩm KHÔNG KÈM GIÁ.
    - **Các sản phẩm có giá **KHÁC** **Liên hệ** thì hãy luôn nói kèm giá khi liệt kê.
    - **CHỈ KHI** khách hàng hỏi giá của sản phẩm có giá "Liên hệ" thì hãy nói "Sản phẩm này em chưa có giá chính xác, nếu anh/chị muốn mua thì em sẽ xem lại và báo lại cho anh chị một mức giá hợp lý".

10.  **Xưng hô và Định dạng:**
    - Luôn xưng "em", gọi khách là "anh/chị".
    - **KHÔNG NÊN** lạm dụng quá nhiều "anh/chị nhé", hãy thỉnh thoảng mới sử dụng để cho tự nhiên hơn.
    - KHÔNG dùng Markdown. Chỉ dùng text thuần.

11.  **Link sản phẩm**
    - Hãy gửi kèm link sản phẩm vào cuối tên sản phẩm **không cần thêm gì hết** khi liệt kê các sản phẩm. Không cần thêm chữ: "Link sản phẩm:" vào.
    - Chỉ gửi kèm link các sản phẩm với các câu hỏi mà khách hàng yêu cầu liệt kê rõ về sản phẩm đó. **KHÔNG** gửi kèm với các câu hỏi chung chung ví dụ: "Có những loại máy hàn nào?".

12.  **Với các câu hỏi bao quát khi khách hàng mới hỏi**
    - Ví dụ: "Shop bạn bán những mặt hàng gì", "Bên bạn có những sản phẩm gi?", hãy trả lời rằng: "Dạ, bên em chuyên kinh doanh các dụng cụ sửa chữa, thiết bị điện tử như máy hàn, kính hiển vi,... Anh/chị đang quan tâm mặt hàng nào để em tư vấn ạ."

13.  **Xử lý lời đồng ý:**
    - Nếu bot ở lượt trước vừa hỏi một câu hỏi Yes/No để đề nghị cung cấp thông tin (ví dụ: "Anh/chị có muốn xem chi tiết không?") và câu hỏi mới nhất của khách là một lời đồng ý (ví dụ: "có", "vâng", "ok"), HÃY thực hiện hành động đã đề nghị.
    - Trong trường hợp này, hãy liệt kê các sản phẩm có trong "DỮ LIỆU CUNG CẤP" theo đúng định dạng danh sách.

14. **Xử lý thông tin không có sẵn:**
    - Nếu khách hàng hỏi về một thông tin không được cung cấp trong "BỐI CẢNH" hoặc "DỮ LIỆU CUNG CẤP" (ví dụ: phí ship, chứng từ, chiết khấu,...), thì **TUYỆT ĐỐI KHÔNG ĐƯỢC BỊA RA**. Hãy trả lời một cách lịch sự rằng: "Dạ, về thông tin này em chưa rõ ạ, em sẽ liên hệ lại cho nhân viên tư vấn để thông tin cho mình sau nhé."

## CÂU TRẢ LỜI CỦA BẠN: ##
"""

def _parse_answer_and_images(llm_response: str, product_infos: list) -> tuple[str, list]:
    """
    Parse kết quả trả về từ LLM.
    """
    if not llm_response:
        return "Dạ em xin lỗi, có lỗi xảy ra trong quá trình tạo câu trả lời.", []

    answer = ""
    product_images = []
    parts = re.split(r'\[PRODUCT_IMAGE\]', llm_response, flags=re.IGNORECASE)

    def clean_name(name: str) -> str:
        return re.sub(r"^[-\s*•+]+", "", name.strip())

    if len(parts) == 2:
        answer = re.sub(r'\[ANSWER\]', '', parts[0], flags=re.IGNORECASE).strip()
        image_lines = [clean_name(l) for l in re.split(r'[\n]+', parts[1]) if l.strip()]
        valid_product_names = set(product_infos)
        product_images = [line for line in image_lines if line in valid_product_names and line.upper() != 'NONE']

        if not product_images and image_lines:
             for line in image_lines:
                 for valid_name in valid_product_names:
                     if line in valid_name:
                         product_images.append(valid_name)
                         break
    else:
        answer = llm_response.strip()

    if not answer and product_images:
        answer = "Dạ đây là hình ảnh sản phẩm em gửi anh/chị tham khảo ạ."

    return answer, product_images


def _get_fallback_response(search_results: List[Dict], needs_product_search: bool) -> str:
    """Tạo câu trả lời dự phòng khi LLM không hoạt động."""
    if needs_product_search:
        if not search_results:
            return "Dạ, em xin lỗi, cửa hàng em chưa kinh doanh sản phẩm này ạ."
        first = search_results[0]
        return (
            f"Dạ, sản phẩm {first.get('product_name', 'N/A')} "
            f"hiện đang có giá {first.get('lifecare_price', 0):,.0f}đ. "
            f"Anh/chị cần tư vấn thêm không ạ?"
        )
    else:
        return "Dạ, em xin lỗi, em không hiểu rõ câu hỏi của anh/chị. Anh/chị có thể hỏi lại không ạ?"
    
def evaluate_and_choose_product(user_query: str, history_text: str, product_candidates: List[Dict], model_choice: str = "gemini", api_key: str = None) -> Dict:
    """
    Sử dụng một lệnh gọi AI duy nhất để vừa đánh giá độ cụ thể của yêu cầu,
    vừa chọn ra sản phẩm phù hợp nhất nếu có thể.
    Trả về một dictionary: {'type': 'PERFECT_MATCH'/'CLOSE_MATCH'/'NO_MATCH', 'score': float, 'product': product_dict/None, 'reason': str/None}
    """
    if not product_candidates:
        return {'type': 'NO_MATCH', 'score': 0.0, 'product': None, 'reason': None}

    prompt_list = ""
    for i, product in enumerate(product_candidates):
        name = product.get("product_name", "")
        props = product.get("properties", "")
        full_name = f"{name} ({props})" if props and str(props) != '0' else name
        prompt_list += f"{i}: {full_name}\n"
    print("Danh sách các sản phẩm trước khi đánh giá:\n", prompt_list)
    prompt = f"""
    Bạn là một AI chuyên phân tích và chọn lựa sản phẩm. Dựa vào yêu cầu của khách hàng và danh sách sản phẩm, hãy thực hiện các nhiệm vụ sau:
    1. Phân tích yêu cầu của khách và danh sách sản phẩm.
    2. Quyết định xem có sản phẩm nào là "PERFECT_MATCH" (khớp hoàn toàn), "CLOSE_MATCH" (khớp loại sản phẩm nhưng sai model/thuộc tính phụ), hay "NO_MATCH" (không liên quan).

    ## Định nghĩa các loại khớp:
    - **PERFECT_MATCH:** Tên, model, và các thuộc tính quan trọng trong yêu cầu của khách khớp chính xác với sản phẩm. Nhưng khi họ đưa thiếu thuộc tính phụ mà sản phẩm đó trong danh sách chỉ có một thuộc tính phụ thì hãy coi đó là PERFECT_MATCH.
    - **CLOSE_MATCH:** Loại sản phẩm chính khớp (ví dụ: cùng là "khay sim") nhưng model hoặc phiên bản lại khác (ví dụ: khách hỏi "cho iPhone 12 Pro Max" nhưng sản phẩm trong danh sách là "cho iPhone 12").
    - **NO_MATCH:** Sản phẩm hoàn toàn không liên quan hoặc không có sản phẩm nào trong danh sách đáp ứng được yêu cầu cơ bản của khách.

    ## QUY TẮC SUY LUẬN THÔNG MINH ##
    - Nếu khách hàng yêu cầu một thuộc tính chung (ví dụ: màu "vàng"), và trong danh sách sản phẩm chỉ có duy nhất một biến thể của thuộc tính đó cho dòng sản phẩm liên quan (ví dụ: chỉ có màu "vàng đồng" cho iPhone 12 Pro Max), HÃY tự động coi đó là sản phẩm khách muốn và trả về "PERFECT_MATCH".
    - Quy tắc này chỉ áp dụng khi chỉ có MỘT lựa chọn hợp lý duy nhất. Nếu có cả "vàng đồng" và "vàng gold", hãy trả về "CLOSE_MATCH" và hỏi lại khách.

    ## QUY TẮC ƯU TIÊN: XỬ LÝ LỜI ĐỒNG Ý SAU KHI GỢI Ý ##
    - Nếu tin nhắn gần nhất của bot là một lời GỢI Ý các sản phẩm tương tự (ví dụ: bắt đầu bằng "Em chưa tìm thấy chính xác..."), và tin nhắn mới nhất của khách hàng là một lời ĐỒNG Ý hoặc CHẤP NHẬN các sản phẩm được gợi ý (ví dụ: "ok", "lấy màu đó đi", "vậy lấy 2 màu đó"), HÃY coi đó là một PERFECT_MATCH.
    - Trong trường hợp này, hãy chọn sản phẩm trong danh sách khớp với gợi ý mà khách hàng vừa đồng ý, và trả về type: "PERFECT_MATCH" và score: 1.0.

    ## PHÂN BIỆT MÔ TẢ VÀ TÊN MODEL/THƯƠNG HIỆU (QUAN TRỌNG) ##
    - Nếu yêu cầu của khách chứa một tên thương hiệu hoặc model cụ thể (ví dụ: "lowe", "kaisi", "quick 861dw"), một sản phẩm CHỈ CÓ THỂ là "PERFECT_MATCH" nếu nó cũng chứa chính xác tên thương hiệu/model đó.
    - Một sản phẩm có cùng loại nhưng khác thương hiệu (ví dụ: khách hỏi "keo lowe" nhưng sản phẩm là "keo mijing") thì BẮT BUỘC phải là "CLOSE_MATCH".
    - Nếu yêu cầu của khách là một mô tả chung (ví dụ: "kính hiển vi 2 mắt") mà có nhiều sản phẩm trong danh sách đều có thể phù hợp thì là "NO_MATCH".

    ## Quy tắc trả về:
    - Hãy trả về kết quả dưới dạng một đối tượng JSON duy nhất.
    - Cấu trúc JSON: {{"type": "PERFECT_MATCH" | "CLOSE_MATCH" | "NO_MATCH", "score": ĐIỂM_SỐ (0.0 đến 1.0), "index": SỐ_THỨ_TỰ | null, "reason": "Lý do không khớp (nếu có)" | null}}
    - score: Bắt buộc. Chấm điểm độ phù hợp từ 0.0 (không liên quan) đến 1.0 (khớp hoàn hảo).
        - PERFECT_MATCH: score phải là 1.0.
        - NO_MATCH: score phải là 0.0.
        - CLOSE_MATCH: score phải > 0.0 và < 1.0. Chấm điểm cao hơn cho các lỗi nhỏ (sai màu, thiếu phụ kiện) và thấp hơn cho các lỗi lớn (sai model sản phẩm).
    - Nếu `type` là "CLOSE_MATCH", trường "reason" là **bắt buộc**. **Lý do phải được viết như một nhân viên đang giải thích cho khách hàng**, ngắn gọn và lịch sự.
    - **Ví dụ cho `reason`**:
        - "sản phẩm này chỉ dành cho iPhone 12, khác với dòng 12 Pro Max của anh/chị ạ."
        - "sản phẩm này chỉ là khay sim, không phải full bộ kèm ổ sim như anh/chị tìm ạ."
        - "em chỉ tìm thấy màu vàng đồng, không có màu vàng gold như anh/chị yêu cầu ạ."
    - Nếu `type` là "PERFECT_MATCH" hoặc "NO_MATCH", "reason" sẽ là null.
    - Nếu không có sản phẩm nào phù hợp, hãy trả về {{"type": "NO_MATCH", "index": null, "reason": null}}

    Lịch sử hội thoại:
    {history_text}
    Yêu cầu mới nhất của khách hàng: "{user_query}"
    Danh sách sản phẩm để chọn:
    {prompt_list}

    JSON kết quả:
    """

    try:
        model = get_gemini_model(api_key=api_key)
        if model:
            response = model.generate_content(prompt)
            json_text = re.search(r'\{.*\}', response.text, re.DOTALL).group(0)
            data = json.loads(json_text)
            
            request_type = data.get("type", "NO_MATCH").upper()
            score = data.get("score", 0.0)
            index = data.get("index")
            reason = data.get("reason")

            product = None
            if index is not None and 0 <= index < len(product_candidates):
                product = product_candidates[index]

            print(f"AI đánh giá: {request_type}, score: {score}, chọn index: {index}, lý do: {reason}")
            
            if request_type in ["PERFECT_MATCH", "CLOSE_MATCH"] and product:
                 return {'type': request_type, 'score': score, 'product': product, 'reason': reason}

            return {'type': 'NO_MATCH', 'score': 0.0, 'product': None, 'reason': None}

    except Exception as e:
        print(f"Lỗi khi AI đánh giá và chọn sản phẩm: {e}")

    # Fallback an toàn
    return {'type': 'NO_MATCH', 'score': 0.0, 'product': None, 'reason': None}

def evaluate_purchase_confirmation(user_query: str, history_text: str, model_choice: str = "gemini", api_key: str = None) -> Dict:
    """
    Sử dụng AI để đánh giá phản hồi của khách hàng khi được hỏi xác nhận đơn hàng.
    Trả về một dictionary: {'decision': 'CONFIRM'/'CANCEL'/'UNCLEAR'}
    """

    prompt = f"""
    Bạn là một AI chuyên phân tích ý định của khách hàng trong ngữ cảnh mua bán.
    Bối cảnh: Bot vừa hỏi khách hàng để XÁC NHẬN việc đặt mua một sản phẩm cụ thể.

    ## Bối cảnh hội thoại:
    {history_text}
    Bot vừa hỏi: "Dạ, em xác nhận anh/chị muốn đặt mua sản phẩm ... đúng không ạ?"
    Khách hàng trả lời: "{user_query}"

    ## Nhiệm vụ của bạn:
    Phân tích câu trả lời của khách hàng và quyết định ý định của họ là "CONFIRM" (đồng ý mua), "CANCEL" (từ chối, hủy), hay "UNCLEAR" (không rõ ràng, hỏi sang chuyện khác).

    - **CONFIRM:** Nếu khách dùng các từ như: "ok", "đúng rồi", "chốt", "lấy cho anh", "vâng", "dạ đúng ạ"...
    - **CANCEL:** Nếu khách dùng các từ như: "không", "thôi", "hủy", "bỏ đi", "không mua nữa", "dạ không ạ"...
    - **UNCLEAR:** Nếu khách hỏi một câu không liên quan (ví dụ: "shop có bán cái khác không?").

    Hãy trả về kết quả dưới dạng JSON với cấu trúc sau:
    {{"decision": "CONFIRM" | "CANCEL" | "UNCLEAR"}}

    JSON kết quả:
    """

    try:
        model = get_gemini_model(api_key=api_key)
        if model:
            from google.generativeai.types import GenerationConfig
            generation_config = GenerationConfig(response_mime_type="application/json")
            response = model.generate_content(prompt, generation_config=generation_config)
            
            data = json.loads(response.text)
            decision = data.get("decision", "UNCLEAR").upper()

            if decision in ["CONFIRM", "CANCEL"]:
                print(f"AI đánh giá ý định xác nhận: {decision}")
                return {'decision': decision}

        # Nếu có lỗi hoặc không xác định được, coi như không rõ ràng
        print("AI đánh giá ý định xác nhận: UNCLEAR")
        return {'decision': 'UNCLEAR'}

    except Exception as e:
        print(f"Lỗi khi AI đánh giá xác nhận đơn hàng: {e}")
        return {'decision': 'UNCLEAR'}

def filter_products_with_ai(user_query: str, history_text: str, product_candidates: List[Dict], api_key: str = None) -> List[Dict]:
    """
    Sử dụng AI để lọc và chọn ra những sản phẩm phù hợp nhất từ danh sách tìm kiếm.
    """
    if not product_candidates or len(product_candidates) <= 1:
        return product_candidates

    prompt_list = ""
    for i, product in enumerate(product_candidates):
        name = product.get("product_name", "")
        category = product.get("category", "")
        props = product.get("properties", "")
        full_name = f"{name} {category} ({props})" if props and str(props) != '0' else f"{name} {category}"
        prompt_list += f"Sản phẩm {i}: {full_name}\n"

    print("Danh sách các sản phẩm trước khi lọc:\n", prompt_list)
    prompt = f"""
    Bạn là một chuyên gia bán hàng thông thái. Nhiệm vụ của bạn là giúp nhân viên tư vấn chọn ra những sản phẩm phù hợp nhất để giới thiệu cho khách hàng.

    ## Bối cảnh:
    - Lịch sử hội thoại:
    {history_text}
    - Câu hỏi mới nhất của khách hàng: "{user_query}"

    ## Danh sách sản phẩm tìm được (có thể chứa sản phẩm không liên quan):
    {prompt_list}

    ## Yêu cầu:
    **QUY TẮC SỐ 1: ƯU TIÊN KHỚP CHÍNH XÁC.**
    - Nếu tên sản phẩm trong câu hỏi của khách khớp **chính xác hoặc gần như chính xác** với một hoặc nhiều sản phẩm trong danh sách, bạn **BẮT BUỘC CHỈ CHỌN** những sản phẩm đó và loại bỏ tất cả những sản phẩm khác.
    - Ví dụ: Khách hỏi "sản phẩm X". Trong danh sách có "Sản phẩm 0: sản phẩm X" và "Sản phẩm 1: sản phẩm Y". Bạn BẮT BUỘC chỉ được trả về `{{"indices": [0]}}`.

    **QUY TẮC QUAN TRỌNG NHẤT: BÁM SÁT LOẠI SẢN PHẨM CỐT LÕI.**
    - Phải xác định **loại sản phẩm cốt lõi** mà khách hàng đang hỏi (ví dụ: "kính hiển vi", "máy hàn", "tô vít").
    - **TUYỆT ĐỐI KHÔNG** chọn các sản phẩm là **phụ kiện** hoặc **bộ phận thay thế** nếu khách hàng đang hỏi về sản phẩm chính.
    - **VÍ DỤ NGUY HIỂM:** Nếu khách hỏi "kính hiển vi Maant", bạn chỉ được chọn sản phẩm là "KÍNH HIỂN VI". **TUYỆT ĐỐI KHÔNG** được chọn "ĐÈN kính hiển vi", "ỐNG NGẮM kính hiển vi", hay "CHÂN ĐẾ kính hiển vi". Tương tự, nếu khách hỏi "máy hàn", không được chọn "mũi hàn".
    - Chỉ chọn phụ kiện khi khách hỏi **trực tiếp** về phụ kiện đó (ví dụ: "có đèn cho kính hiển vi không?").

    Dựa vào bối cảnh và câu hỏi của khách, hãy xem xét kỹ từng sản phẩm trong danh sách và chọn ra những sản phẩm **THỰC SỰ LIÊN QUAN** và hợp lý nhất để tư vấn.
    - **Ví dụ:** Nếu khách hỏi "Box JC V1SE", bạn chỉ được chọn các sản phẩm có tên chính xác là "Box JC V1SE" hoặc các phiên bản/combo trực tiếp của nó. **TUYỆT ĐỐI KHÔNG** chọn các sản phẩm khác dù có chữ "Box" hoặc "JC".

    ## Quy tắc quan trọng chung cho tất cả sản phẩm:
    - **KHÔNG** chọn các sản phẩm không liên quan với câu hỏi của khách. Hãy trả ra các kết quả rỗng nếu không có sản phẩm khách tìm. Ví dụ: khách hỏi "tai nghe", nếu không có tai nghe thì trả ra rỗng, không trả ra các sản phẩm như đế tai nghe, dụng cụ vệ sinh tai nghe,...

    Hãy trả về một đối tượng JSON chứa một key duy nhất là "indices", là một danh sách (list) các SỐ THỨ TỰ (index) của những sản phẩm bạn đã chọn.
    Ví dụ: {{"indices": [0, 2, 5]}}
    Nếu không có sản phẩm nào thực sự phù hợp, hãy trả về một danh sách rỗng: {{"indices": []}}

    JSON kết quả:
    """

    try:
        model = get_gemini_model(api_key=api_key)
        if model:
            from google.generativeai.types import GenerationConfig
            generation_config = GenerationConfig(response_mime_type="application/json")
            response = model.generate_content(prompt, generation_config=generation_config)
            data = json.loads(response.text)
            
            indices = data.get("indices", [])
            if not isinstance(indices, list):
                return product_candidates

            if not indices:
                print("AI không chọn sản phẩm nào. Trả về danh sách rỗng.")
                return []

            filtered_products = [product_candidates[i] for i in indices if 0 <= i < len(product_candidates)]
            
            print(f"AI đã lọc sản phẩm. Kết quả: {len(filtered_products)}/{len(product_candidates)} sản phẩm được chọn.")
            return filtered_products

    except Exception as e:
        print(f"Lỗi khi AI lọc sản phẩm: {e}")

    return product_candidates